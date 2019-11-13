import inspect
import json

import re
import socket
import time
from collections import defaultdict
from contextlib import contextmanager
from ctypes import *
from datetime import datetime
from pathlib import Path
from typing import Union, Optional, Match

from paho.mqtt.client import MQTTMessage
from googletrans import Translator

import core.commons.model.Slot as slotModel
from core.base.model.Manager import Manager
from core.commons import constants
from core.commons.model.PartOfDay import PartOfDay
from core.dialog.model.DialogSession import DialogSession

class CommonsManager(Manager):

	ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
	VERSION_PARSER_REGEX = re.compile('(?P<mainVersion>\d+)\.(?P<updateVersion>\d+)(\.(?P<hotfix>\d+))?(-(?P<releaseType>a|b|rc)(?P<releaseNumber>\d+))?')
	
	def __init__(self):
		super().__init__('Commons')


	@staticmethod
	@contextmanager
	def shutUpAlsaFFS():
		asound = cdll.LoadLibrary('libasound.so')
		asound.snd_lib_error_set_handler(c_error_handler)
		yield
		asound.snd_lib_error_set_handler(None)


	@staticmethod
	def getFunctionCaller(depth: int = 3) -> str:
		return inspect.getmodulename(inspect.stack()[depth][1])


	def isEqualTranslated(self, baseString: str, compareTo: str, module: str = 'system') -> bool:
		"""
		Compares the basestring to the compareTo string. compareTo string if the key in the strings file
		If the string in LanguageManager contains more than one value, each value will be compared and True is
		returned at first match

		:param module: If empty takes the system strings json
		:param baseString: the base string to compare
		:param compareTo: the key of the string json to compare to
		:return: bool
		"""
		baseString = baseString.strip().lower()
		return any(x.strip().lower() == baseString for x in self.LanguageManager.getStrings(compareTo, module))


	@staticmethod
	def dictMaxValue(d: dict) -> str:
		return max(d, key=d.get)


	@staticmethod
	def rootDir() -> str:
		return str(Path(__file__).resolve().parent.parent.parent)


	@staticmethod
	def payload(message: MQTTMessage) -> dict:
		try:
			payload = json.loads(message.payload)
		except (ValueError, TypeError):
			payload = dict()
		
		if payload is True:
			payload = {'true': 'true'}
		elif payload is False:
			payload = {'false': 'false'}
		
		return payload


	@classmethod
	def parseSlotsToObjects(cls, message: MQTTMessage) -> dict:
		slots = defaultdict(list)
		data = cls.payload(message)
		for slotData in data.get('slots', dict()):
			slot = slotModel.Slot(slotData)
			slots[slot.slotName].append(slot)
		return slots


	@classmethod
	def parseSlots(cls, message: MQTTMessage) -> dict:
		data = cls.payload(message)
		return {slot['slotName']: slot['rawValue'] for slot in data.get('slots', dict())}


	@classmethod
	def parseSessionId(cls, message: MQTTMessage) -> Union[str, bool]:
		data = cls.payload(message)
		return data.get('sessionId', False)


	@classmethod
	def parseCustomData(cls, message: MQTTMessage) -> dict:
		try:
			data = cls.payload(message)
			return json.loads(data['customData'])
		except (ValueError, TypeError, KeyError):
			return dict()


	@classmethod
	def parseSiteId(cls, message: MQTTMessage) -> str:
		data = cls.payload(message)
		if 'siteId' in data:
			return data['siteId'].replace('_', ' ')  # WTF!! This is highly no no no!!!
		else:
			return data.get('IPAddress', constants.DEFAULT_SITE_ID)


	@staticmethod
	def smartSleep(wait: int):
		startTime = time.time()
		while time.time() - startTime < wait:
			continue


	@staticmethod
	def clamp(x: float, minimum: float, maximum: float) -> float:
		return max(minimum, min(x, maximum))


	@staticmethod
	def angleToCardinal(angle: float) -> str:
		cardinals = ['north', 'north east', 'east', 'south east', 'south', 'south west', 'west', 'north west']
		return cardinals[int(((angle + 45 / 2) % 360) / 45)]


	def partOfTheDay(self) -> str:
		hour = datetime.now().hour

		if self.UserManager.checkIfAllUser('sleeping'):
			return PartOfDay.SLEEPING.value
		elif 23 <= hour < 5:
			return PartOfDay.NIGHT.value
		elif 5 <= hour < 7:
			return PartOfDay.EARLY_MORNING.value
		elif 7 <= hour < 12:
			return PartOfDay.MORNING.value
		elif 12 <= hour < 18:
			return PartOfDay.AFTERNOON.value
		else:
			return PartOfDay.EVENING.value


	@staticmethod
	def isYes(session: DialogSession) -> bool:
		try:
			return session.slotsAsObjects['Answer'][0].value['value'] == 'yes'
		except (TypeError, KeyError, IndexError, AttributeError):
			return False


	@staticmethod
	def getDuration(session: DialogSession) -> int:
		slots = session.slotsAsObjects
		duration = 0
		if 'Duration' in slots and slots['Duration'][0].entity == 'snips/duration':
			try:
				values = slots['Duration'][0].value
				duration += values['seconds']
				duration += values['minutes'] * 60
				duration += values['hours'] * 60 * 60
				duration += values['days'] * 24 * 60 * 60
				duration += values['weeks'] * 7 * 24 * 60 * 60
				duration += values['months'] * 4 * 7 * 24 * 60 * 60
			except (TypeError, KeyError):
				pass

		return duration


	@classmethod
	def toCamelCase(cls, string: str, replaceSepCharacters: bool = False, sepCharacters: tuple = None) -> str:
		join = cls.toPascalCase(string, replaceSepCharacters, sepCharacters)
		return join[0].lower() + join[1:]


	@staticmethod
	def toPascalCase(string: str, replaceSepCharacters: bool = False, sepCharacters: tuple = None) -> str:
		if replaceSepCharacters:
			for char in sepCharacters or ('-', '_'):
				string = string.replace(char, ' ')

		return ''.join(x.capitalize() for x in string.split(' '))


	@staticmethod
	def isSpelledWord(string: str) -> bool:
		"""
		Empirical way to check if a string is something spelled by the user by counting the theoretical length of the string against
		its theoretical spelled length
		:param string: string to check
		:return: bool
		"""
		return len(string) == (len(string.replace(' ', '').strip()) * 2) - 1


	def cleanRoomNameToSiteId(self, roomName: str) -> str:
		"""
		User might answer "in the living room" when asked for a room. In that case it should be turned into "living_room"
		:param roomName: str: original captured name
		:return: str: formated room name to site id
		"""

		parasites = self.LanguageManager.getStrings(key='inThe')

		for parasite in parasites:
			if parasite in roomName:
				roomName = roomName.replace(parasite, '')
				break

		return roomName.strip().replace(' ', '_')


	@staticmethod
	def getLocalIp() -> str:
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		try:
			sock.connect(('10.255.255.255', 1))
			ip = sock.getsockname()[0]
		except:
			ip = '127.0.0.1'
		finally:
			sock.close()
		return ip


	@staticmethod
	def indexOf(sub: str, string: str) -> int:
		try:
			return string.index(sub)
		except ValueError:
			return -1


	def translate(self, text: Union[str, list], destLang: str, srcLang: str = None) -> Union[str, list]:
		"""
		Translates a string or a list of strings into a different language using
		google translator. Especially helpful when a api is only available in one
		language, but the module should support other languages aswell.

		:param text: string or list of strings to translate
		:param destLang: language to translate to (ISO639-1 code)
		:param srcLang: source language to translate (ISO639-1 code)
		:return: translated string or list of strings
		"""
		if not destLang:
			destLang = self.LanguageManager.activeLanguage

		if srcLang == destLang:
			return text

		kwargs = {
			'text': text,
			'dest': destLang
		}
		if srcLang:
			kwargs['src'] = destLang

		if isinstance(text, str):
			return Translator().translate(**kwargs).text
		return [result.text for result in Translator().translate(**kwargs)]


	@classmethod
	def parseVersionNumber(cls, version: str) -> Optional[Match[str]]:
		return cls.VERSION_PARSER_REGEX.search(str(version))


# noinspection PyUnusedLocal
def py_error_handler(filename, line, function, err, fmt):
	pass

c_error_handler = CommonsManager.ERROR_HANDLER_FUNC(py_error_handler)
