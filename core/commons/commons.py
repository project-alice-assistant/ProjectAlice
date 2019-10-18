import functools
import inspect
import json
import socket
import time
import warnings
from collections import defaultdict
from contextlib import contextmanager
from ctypes import *
from datetime import datetime
from pathlib import Path
from typing import Union, Callable

from paho.mqtt.client import MQTTMessage
from googletrans import Translator

import core.commons.model.Slot as slotModel
from core.base.SuperManager import SuperManager
from core.commons import constants
from core.commons.model.PartOfDay import PartOfDay
from core.dialog.model import DialogSession

ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)

# noinspection PyUnusedLocal
def py_error_handler(filename, line, function, err, fmt):
	pass


c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)


@contextmanager
def shutUpAlsaFFS():
	asound = cdll.LoadLibrary('libasound.so')
	asound.snd_lib_error_set_handler(c_error_handler)
	yield
	asound.snd_lib_error_set_handler(None)


def getFunctionCaller(depth: int = 3) -> str:
	return inspect.getmodulename(inspect.stack()[depth][1])


def isEqualTranslated(baseString: str, compareTo: str, module: str = 'system') -> bool:
	"""
	Compares the basestring to the compareTo string. compareTo string if the key in the strings file
	If the string in LanguageManager contains more than one value, each value will be compared and True is
	returned at first match

	:param module: If empty takes the system strings json
	:param baseString: the base string to compare
	:param compareTo: the key of the string json to compare to
	:return: bool
	"""
	strings = SuperManager.getInstance().languageManager.getStrings(compareTo, module)
	baseString = baseString.strip().lower()
	for string in strings:
		if baseString == string.strip().lower():
			return True
	return False


def deprecated(func):
	"""
	https://stackoverflow.com/questions/2536307/decorators-in-the-python-standard-lib-deprecated-specifically
	This is a decorator which can be used to mark functions
	as deprecated. It will result in a warning being emitted
	when the function is used.
	"""


	@functools.wraps(func)
	def new_func(*args, **kwargs):
		warnings.simplefilter('always', DeprecationWarning)  # turn off filter
		warnings.warn(f'Call to deprecated function {func.__name__}.',
					  category=DeprecationWarning,
					  stacklevel=2)
		warnings.simplefilter('default', DeprecationWarning)  # reset filter
		return func(*args, **kwargs)


	return new_func


def dictMaxValue(d: dict) -> str:
	return max(d, key=d.get)


def rootDir() -> str:
	return str(Path(__file__).resolve().parent.parent.parent)


def getDatabaseFile() -> str:
	return str(Path('system/database/data.db'))


def payload(message: MQTTMessage) -> dict:
	p = ''
	try:
		p = message.payload
		p = p.decode()
		return json.loads(p)
	except (UnicodeDecodeError, AttributeError):
		try:
			return json.loads(message.payload)
		except ValueError:
			raise
	except ValueError:
		return {p: p}
	except:
		return dict()


def parseSlotsToObjects(message: MQTTMessage) -> dict:
	slots = defaultdict(list)
	data = payload(message)
	for slotData in data.get('slots', dict()):
		slot = slotModel.Slot(slotData)
		slots[slot.slotName].append(slot)
	return slots


def parseSlots(message: MQTTMessage) -> dict:
	data = payload(message)
	return { slot['slotName']: slot['rawValue'] for slot in data.get('slots', dict()) }


def parseSessionId(message: MQTTMessage) -> Union[str, bool]:
	data = payload(message)
	return data.get('sessionId', False)


def parseCustomData(message: MQTTMessage) -> dict:
	try:
		data = payload(message)
		return json.loads(data['customData'])
	except:
		return dict()


def parseSiteId(message: MQTTMessage) -> str:
	data = payload(message)
	if 'siteId' in data:
		return data['siteId'].replace('_', ' ')  # WTF!! This is highly no no no!!!
	else:
		return data.get('IPAddress', constants.DEFAULT_SITE_ID)


def smartSleep(wait: int):
	startTime = time.time()
	while time.time() - startTime < wait:
		continue


def clamp(x: float, minimum: float, maximum: float) -> float:
	return max(minimum, min(x, maximum))


def angleToCardinal(angle: float) -> str:
	cardinals = ['north', 'north east', 'east', 'south east', 'south', 'south west', 'west', 'north west']
	return cardinals[int(((angle + 45 / 2) % 360) / 45)]


def partOfTheDay() -> str:
	hour = datetime.now().hour

	if SuperManager.getInstance().userManager.checkIfAllUser('sleeping'):
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


def isYes(session: DialogSession) -> bool:
	slots = session.slotsAsObjects
	try:
		return slots['Answer'][0].value['value'] == 'yes'
	except:
		return False


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
		except:
			pass

	return duration


def toCamelCase(string: str, replaceSepCharacters: bool = False, sepCharacters: tuple = None) -> str:
	join = toPascalCase(string, replaceSepCharacters, sepCharacters)
	return join[0].lower() + join[1:]


def toPascalCase(string: str, replaceSepCharacters: bool = False, sepCharacters: tuple = None) -> str:
	if replaceSepCharacters:
		for char in sepCharacters or ('-', '_'):
			string = string.replace(char, ' ')

	return ''.join(x.capitalize() for x in string.split(' '))


def isSpelledWord(string: str) -> bool:
	"""
	Empirical way to check if a string is something spelled by the user by counting the theoretical length of the string against
	its theoretical spelled length
	:param string: string to check
	:return: bool
	"""

	return len(string) == (len(string.replace(' ', '').strip()) * 2) - 1


def cleanRoomNameToSiteId(roomName: str) -> str:
	"""
	User might answer "in the living room" when asked for a room. In that case it should be turned into "living_room"
	:param roomName: str: original captured name
	:return: str: formated room name to site id
	"""

	parasites = SuperManager.getInstance().languageManager.getStrings(key='inThe')

	for parasite in parasites:
		if parasite in roomName:
			roomName = roomName.replace(parasite, '')
			break

	return roomName.strip().replace(' ', '_')


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


def indexOf(sub: str, string: str) -> int:
	try:
		return string.index(sub)
	except ValueError:
		return -1


def online(text: str = '', offlineHandler: Callable = None):
	"""
	(return a) decorator to mark a function that required ethernet.

	This decorator can be used (with or or without parameters) to define
	a function that requires ethernet. In the Default mode without arguments shown
	in the example it will either execute whats in the function or when alice is
	offline return a random offline answer. Using the parameters:
		@online(text=<myText>)
	a own text can be used when being offline aswell and using the parameters:
		@online(offlineHandler=<myFunc>)
	a own offline handler can be called, which is especially helpful when the intent wants to
	use endDialog, continueDialog ... inside the decorated function -> does not return the text

	:param text:
	:param offlineHandler:
	:return: return value of function or random offline string in the current language
	Examples:
		An intent that requires ethernet can be defined the following way:

		def onMessage(self, intent: str, session: DialogSession) -> bool:
			if not self.filterIntent(intent, session):
				return False
			if intent == self._INTENT_EXAMPLE:
				self.endDialog(sessionId=session.sessionId, text=self.exampleIntent())
			elif intent == self._INTENT_EXAMPLE_2:
				self.endDialog(sessionId=session.sessionId, text=self.exampleIntent2())
			elif intent == self._INTENT_EXAMPLE_3:
				self.exampleIntent2(session)
			
			return True

		@online
		def exampleIntent(self) -> str:
			request = requests.get('http://api.open-notify.org')
			return request.text

		@online(text='offlineText')
		def exampleIntent2(self) -> str:
			request = requests.get('http://api.open-notify.org')
			return request.text
		
		def offlineHandler(self, session: DialogSession):
			self.endDialog(sessionId=session.sessionId, text='offlineText')

		@online(text='offlineText')
		def exampleIntent2(self, session: DialogSession):
			request = requests.get('http://api.open-notify.org')
			self.endDialog(sessionId=session.sessionId, text=request.text)
	"""

	def argumentWrapper(func):
		def functionWrapper(*args, **kwargs):
			internetManager = SuperManager.getInstance().internetManager
			if internetManager.online:
				try:
					return func(*args, **kwargs)
				except:
					internetManager._checkOnlineState()
					if internetManager.online:
						raise
			
			if callable(text) or not text and not offlineHandler:
				return SuperManager.getInstance().talkManager.randomTalk('offline', module='system')
			if offlineHandler:
				return offlineHandler(*args, **kwargs)
			return text

		return functionWrapper

	if callable(text):
		return argumentWrapper(text)
	return argumentWrapper


def translate(text: Union[str, list], destLang: str, srcLang: str = None) -> Union[str, list]:
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
		destLang = SuperManager.getInstance().languageManager.activeLanguage
	
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
