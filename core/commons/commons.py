import inspect
import json
import socket
import time
from collections import defaultdict
from contextlib import contextmanager
from ctypes import *
from datetime import datetime
from typing import Union

import functools
from pathlib import Path
import warnings
from paho.mqtt.client import MQTTMessage

import core.base.Managers as managers
import core.commons.model.Slot as slotModel
from core.commons.model.PartOfDay import PartOfDay

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
	strings = managers.LanguageManager.getStrings(compareTo, module)
	for string in strings:
		if baseString.strip().lower() == string.strip().lower():
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
		warnings.warn("Call to deprecated function {}.".format(func.__name__),
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
	try:
		return json.loads(message.payload)
	except:
		try:
			return json.loads(message.payload.decode())
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
	return dict((slot['slotName'], slot['rawValue']) for slot in data.get('slots', dict()))


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
		return data['siteId'].replace('_', ' ') #WTF!! This is highly no no no!!!
	else:
		return data.get('IPAddress', 'default')


def smartSleep(wait: int):
	startTime = time.time()
	while time.time() - startTime < wait:
		continue


def clamp(x: float, minimum: float, maximum: float) -> float:
	return max(minimum, min(x, maximum))


def angleToCardinal(angle: float) -> str:
	cardinals = ['north', 'north east', 'east', 'south east', 'south', 'south west', 'west', 'north west']
	return cardinals[int(((angle+45/2)%360) / 45)]


def partOfTheDay() -> str:
	hour = int(datetime.now().strftime('%H'))

	if managers.UserManager.checkIfAllUser('sleeping'):
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


def isYes(msg: MQTTMessage) -> bool:
	slots = parseSlotsToObjects(message=msg)
	try:
		return slots['Answer'][0].value['value'] == 'yes'
	except:
		return False


def getDuration(msg: MQTTMessage) -> int:
	slots = parseSlotsToObjects(msg)
	duration = 0
	if 'Duration' in slots and slots['Duration'][0].entity == 'snips/duration':
		try:
			values = slots['duration'][0].value
			duration += values['seconds']
			duration += values['minutes'] * 60
			duration += values['hours'] * 60 * 60
			duration += values['days'] * 24 * 60 * 60
			duration += values['weeks'] * 7 * 24 * 60 * 60
			duration += values['months'] * 4 * 7 * 24 * 60 * 60
		except Exception:
			pass

	return duration


def toCamelCase(string: str, replaceSepCharacters: bool = False, sepCharacters: tuple = None) -> str:
	if replaceSepCharacters:
		if not sepCharacters: sepCharacters = ('-', '_')
		for char in sepCharacters:
			string.replace(char, ' ')

	return ''.join(x.capitalize() for x in string.split(' '))


def isSpelledWord(string: str) -> bool:

	"""
	Empirical way to check if a string is something spelled by the user by counting the theoretical length of the string against
	its theoretical spelled length
	:param string: string to check
	:return: bool
	"""

	string = str(string)
	l = len(string)
	s = string.replace(' ', '').strip()
	return l == (len(s) * 2) - 1


def cleanRoomNameToSiteId(roomName: str) -> str:
	"""
	User might answer "in the living room" when asked for a room. In that case it should be turned into "living_room"
	:param roomName: str: original captured name
	:return: str: formated room name to site id
	"""

	parasites = managers.LanguageManager.getStrings(key='inThe')

	for parasite in parasites:
		if parasite in roomName:
			roomName = str(roomName).replace(parasite, '')
			break

	return str(roomName).strip().replace(' ', '_')


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

def isInt(string: str) -> bool:
	try:
		int(string)
		return True
	except ValueError:
		return False


def indexOf(sub: str, string: str) -> int:
	try:
		return string.index(sub)
	except ValueError:
		return -1
