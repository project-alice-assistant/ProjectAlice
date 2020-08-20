import inspect
import json
import socket
import string
import subprocess
import time
from collections import defaultdict
from contextlib import contextmanager, suppress
from ctypes import *
from datetime import datetime
from pathlib import Path
from typing import Any, Union

import hashlib
import random
import requests
import tempfile
from googletrans import Translator
from paho.mqtt.client import MQTTMessage

import core.commons.model.Slot as slotModel
from core.base.model.Manager import Manager
from core.commons import constants
from core.commons.model.PartOfDay import PartOfDay
from core.dialog.model.DialogSession import DialogSession


class CommonsManager(Manager):

	ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)

	def __init__(self):
		super().__init__(name='Commons')


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


	def isEqualTranslated(self, baseString: str, compareTo: str, skill: str = 'system') -> bool:
		"""
		Compares the basestring to the compareTo string. compareTo string if the key in the strings file
		If the string in LanguageManager contains more than one value, each value will be compared and True is
		returned at first match

		:param skill: If empty takes the system strings json
		:param baseString: the base string to compare
		:param compareTo: the key of the string json to compare to
		:return: bool
		"""
		baseString = baseString.strip().lower()
		return any(x.strip().lower() == baseString for x in self.LanguageManager.getStrings(compareTo, skill))


	@staticmethod
	def dictMaxValue(dictionary: dict) -> Any:
		return max(dictionary, key=dictionary.get)


	@staticmethod
	def rootDir() -> str:
		return str(Path(__file__).resolve().parent.parent.parent)


	@staticmethod
	def payload(message: MQTTMessage) -> dict:
		try:
			payload = json.loads(message.payload)
		except (ValueError, TypeError):
			var = message.topic.split('/')[-1]
			payload = {var: message.payload}

		return payload


	@classmethod
	def parseSlotsToObjects(cls, message: MQTTMessage) -> dict:
		slots = defaultdict(list)
		data = cls.payload(message)

		if not isinstance(data, dict):
			return dict()

		for slotData in data.get('slots', dict()):
			slot = slotModel.Slot(**slotData)
			slots[slot.slotName].append(slot)
		return slots


	@classmethod
	def parseSlots(cls, message: MQTTMessage) -> dict:
		data = cls.payload(message)

		if not isinstance(data, dict):
			return dict()

		return {slot['slotName']: slot['rawValue'] for slot in data.get('slots', dict())}


	@classmethod
	def parseSessionId(cls, message: MQTTMessage) -> Union[str, bool]:
		data = cls.payload(message)

		if not isinstance(data, dict):
			return False

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

		if not isinstance(data, dict):
			return constants.UNKNOWN

		if 'siteId' in data:
			return data['siteId'].replace('_', ' ')
		else:
			from core.base.SuperManager import SuperManager
			return data.get('IPAddress', SuperManager.getInstance().configManager.getAliceConfigByName('deviceName'))


	@staticmethod
	def smartSleep(wait: int):
		startTime = time.time()
		while time.time() - startTime < wait:
			continue


	@staticmethod
	def clamp(number: float, minimum: float, maximum: float) -> float:
		return max(minimum, min(number, maximum))


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
			with suppress(TypeError, KeyError):
				values = slots['Duration'][0].value
				duration += values['seconds']
				duration += values['minutes'] * 60
				duration += values['hours'] * 60 * 60
				duration += values['days'] * 24 * 60 * 60
				duration += values['weeks'] * 7 * 24 * 60 * 60
				duration += values['months'] * 4 * 7 * 24 * 60 * 60

		return duration


	@classmethod
	def toCamelCase(cls, theString: str, replaceSepCharacters: bool = False, sepCharacters: tuple = None) -> str:
		join = cls.toPascalCase(theString, replaceSepCharacters, sepCharacters)
		return join[0].lower() + join[1:]


	@staticmethod
	def toPascalCase(theString: str, replaceSepCharacters: bool = False, sepCharacters: tuple = None) -> str:
		if replaceSepCharacters:
			for char in sepCharacters or ('-', '_'):
				theString = theString.replace(char, ' ')

		return ''.join(x.capitalize() for x in theString.split(' '))


	@staticmethod
	def isSpelledWord(theString: str) -> bool:
		"""
		Empirical way to check if a string is something spelled by the user by counting the theoretical length of the string against
		its theoretical spelled length
		:param theString: string to check
		:return: bool
		"""
		return len(theString) == (len(theString.replace(' ', '').strip()) * 2) - 1


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
	def indexOf(sub: str, theString: str) -> int:
		try:
			return theString.index(sub)
		except ValueError:
			return -1


	@staticmethod
	def isWritable(path: Path):
		try:
			test = tempfile.TemporaryFile(dir=path)
			test.close()
		except:
			return False

		return True


	def translate(self, text: Union[str, list], destLang: str = None, srcLang: str = None) -> Union[str, list]:
		"""
		Translates a string or a list of strings into a different language using
		google translator. Especially helpful when a api is only available in one
		language, but the skill should support other languages aswell.

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


	def runRootSystemCommand(self, commands: list, shell: bool = False, stdout = subprocess.PIPE, stderr = subprocess.PIPE) -> subprocess.CompletedProcess:
		if commands[0] != 'sudo':
			commands.insert(0, 'sudo')
		return self.runSystemCommand(commands, shell=shell, stdout=stdout, stderr=stderr)


	@staticmethod
	def runSystemCommand(commands: list, shell: bool = False, stdout = subprocess.PIPE, stderr = subprocess.PIPE) -> subprocess.CompletedProcess:
		return subprocess.run(commands, shell=shell, stdout=stdout, stderr=stderr)


	def downloadFile(self, url: str, dest: str) -> bool:
		if not self.Commons.rootDir() in dest:
			dest = f'{self.Commons.rootDir()}/{dest}'

		try:
			with requests.get(url, stream=True) as r:
				r.raise_for_status()
				with Path(dest).open('wb') as fp:
					for chunk in r.iter_content(chunk_size=8192):
						if chunk:
							fp.write(chunk)
			return True
		except Exception as e:
			self.logWarning(f'Failed downloading file: {e}')
			return False


	@staticmethod
	def fileChecksum(file: Path) -> str:
		return hashlib.blake2b(file.read_bytes()).hexdigest()


	@staticmethod
	def randomString(length: int) -> str:
		chars = string.ascii_letters + string.digits
		return ''.join(random.choice(chars) for _ in range(length))


	def randomNumber(self, length: int) -> int:
		digits = string.digits
		number = ''.join(random.choice(digits) for _ in range(length))
		return int(number) if not number.startswith('0') else self.randomNumber(length)

# noinspection PyUnusedLocal
def py_error_handler(filename, line, function, err, fmt): #NOSONAR
	# Errors are handled by our loggers
	pass


c_error_handler = CommonsManager.ERROR_HANDLER_FUNC(py_error_handler) #NOSONAR
