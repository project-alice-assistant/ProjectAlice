#  Copyright (c) 2021
#
#  This file, test_CommonsManager.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:50 CEST

import unittest
from unittest import mock
from unittest.mock import MagicMock
from uuid import UUID

from core.commons.CommonsManager import CommonsManager


class TestCommonsManager(unittest.TestCase):

	def test_getFunctionCaller(self):
		self.assertEqual(CommonsManager.getFunctionCaller(1), 'test_CommonsManager')


	@mock.patch('core.commons.CommonsManager.CommonsManager.LanguageManager')
	def test_isEqualTranslated(self, mock_LanguageManager):
		commonsManager = CommonsManager()
		mock_LanguageManager.getStrings.return_value = ['String1', ' strIng2']
		self.assertTrue(commonsManager.isEqualTranslated('string1', 'compareTo', 'skill'))
		mock_LanguageManager.getStrings.called_once_with('compareTo', 'skill')
		self.assertTrue(commonsManager.isEqualTranslated('string2 ', 'compareTo', 'skill'))
		self.assertFalse(commonsManager.isEqualTranslated('string3', 'compareTo', 'skill'))


	def test_dictMaxValue(self):
		self.assertEqual(
			CommonsManager.dictMaxValue({'first': 1, 'second': 3, 'third': 2}),
			'second'
		)


	def test_payload(self):
		class MQTTMessage(object):

			def __init__(self, payload):
				self.payload = payload
				self.topic = 'test'


		self.assertEqual(
			CommonsManager.payload(MQTTMessage(None)),
			{'test': None}
		)
		self.assertEqual(
			CommonsManager.payload(MQTTMessage(b'\x81')),
			{'test': b'\x81'}
		)
		self.assertEqual(
			CommonsManager.payload(MQTTMessage('{"test": 2}')),
			{'test': 2}
		)
		self.assertEqual(
			CommonsManager.payload(MQTTMessage(b'{"test": 2}')),
			{'test': 2}
		)
		self.assertEqual(
			CommonsManager.payload(MQTTMessage('true')),
			{'test': True}
		)
		self.assertEqual(
			CommonsManager.payload(MQTTMessage('false')),
			{'test': False}
		)
		self.assertEqual(
			CommonsManager.payload(MQTTMessage(b'true')),
			{'test': True}
		)


	def test_parseSlotsToObjects(self):
		class MQTTMessage(object):

			def __init__(self, payload):
				self.payload = payload
				self.topic = 'test'


		self.assertEqual(
			CommonsManager.parseSlotsToObjects(MQTTMessage(None)),
			dict()
		)


	def test_parseSlots(self):
		class MQTTMessage(object):

			def __init__(self, payload):
				self.payload = payload
				self.topic = 'test'


		self.assertEqual(
			CommonsManager.parseSlots(MQTTMessage(None)),
			dict()
		)
		message = MQTTMessage('{"slots": [\
			{"slotName": "slotName1", "rawValue": "rawValue1"},\
			{"slotName": "slotName2", "rawValue": "rawValue2"}]}')
		self.assertEqual(
			CommonsManager.parseSlots(message),
			{"slotName1": "rawValue1", "slotName2": "rawValue2"}
		)


	def test_parseSessionId(self):
		class MQTTMessage(object):

			def __init__(self, payload):
				self.payload = payload
				self.topic = 'test'


		self.assertEqual(
			CommonsManager.parseSessionId(MQTTMessage(None)), False)
		self.assertEqual(
			CommonsManager.parseSessionId(MQTTMessage('{"sessionId": "sessionIdValue"}')), "sessionIdValue")


	def test_parseCustomData(self):
		class MQTTMessage(object):

			def __init__(self, payload):
				self.payload = payload
				self.topic = 'test'


		self.assertEqual(
			CommonsManager.parseCustomData(MQTTMessage(None)),
			dict()
		)
		self.assertEqual(
			CommonsManager.parseCustomData(MQTTMessage(b'{"customData": "nonJsonString"}')),
			dict()
		)
		self.assertEqual(
			CommonsManager.parseCustomData(MQTTMessage(b'{"customData": null}')),
			dict()
		)
		self.assertEqual(
			CommonsManager.parseCustomData(MQTTMessage('{"customData": "{\\"test\\": \\"test\\"}"}')),
			{'test': 'test'}
		)


	@mock.patch('core.base.SuperManager.SuperManager')
	def test_parseDeviceUid(self, mock_superManager):
		class MQTTMessage(object):

			def __init__(self, payload):
				self.payload = payload
				self.topic = 'test'


		# mock SuperManager
		mock_instance = MagicMock()
		mock_superManager.getInstance.return_value = mock_instance
		mock_instance.configManager.getAliceConfigByName.return_value = 'uuid'

		self.assertEqual(
			CommonsManager.parseDeviceUid(MQTTMessage('{"siteId": "uid", "IPAddress": "127.0.0.1"}')),
			'uid'
		)

		self.assertEqual(
			CommonsManager.parseDeviceUid(MQTTMessage('{"IPAddress": "127.0.0.1"}')),
			'127.0.0.1'
		)

		self.assertEqual(
			CommonsManager.parseDeviceUid(MQTTMessage('{}')),
			'uuid'
		)


	def test_getDuration(self):
		"""Test getDuration method"""


		class DialogSession(object):

			def __init__(self, slotsAsObjects: dict):
				self.slotsAsObjects = slotsAsObjects


		class TimeObject(object):

			def __init__(self, value: dict, entity: str = 'snips/duration'):
				self.value = value
				self.entity = entity


		timeDict = {
			'seconds': 6,
			'minutes': 5,
			'hours'  : 4,
			'days'   : 3,
			'weeks'  : 2,
			'months' : 1
		}

		session = DialogSession({'Duration': [TimeObject(timeDict)]})
		self.assertEqual(CommonsManager.getDuration(session), 3902706)

		session = DialogSession({'Duration': [TimeObject(timeDict, 'customDurationIntent')]})
		self.assertEqual(CommonsManager.getDuration(session), 0)

		session = DialogSession({'Duration': [TimeObject(dict())]})
		self.assertEqual(CommonsManager.getDuration(session), 0)


	def test_toCamelCase(self):
		"""Test whether string gets correctly converted to camel case"""
		self.assertEqual(CommonsManager.toCamelCase('example string'), 'exampleString')
		self.assertEqual(CommonsManager.toCamelCase('Example-string_2', replaceSepCharacters=True), 'exampleString2')
		self.assertEqual(CommonsManager.toCamelCase('Example+string/2', replaceSepCharacters=True, sepCharacters=('+', '/')), 'exampleString2')


	def test_toPascalCase(self):
		"""Test whether string gets correctly converted to pascal case"""
		self.assertEqual(CommonsManager.toPascalCase('example string'), 'ExampleString')
		self.assertEqual(CommonsManager.toPascalCase('Example-string_2', replaceSepCharacters=True), 'ExampleString2')
		self.assertEqual(CommonsManager.toPascalCase('Example+string/2', replaceSepCharacters=True, sepCharacters=('+', '/')), 'ExampleString2')


	def test_isSpelledWord(self):
		"""Test whether string is spelled"""
		self.assertTrue(CommonsManager.isSpelledWord('e x a m p l e'))
		self.assertFalse(CommonsManager.isSpelledWord('example'))
		self.assertFalse(CommonsManager.isSpelledWord('e x am p l e'))


	def test_clamp(self):
		self.assertEqual(CommonsManager.clamp(4.5, 4, 5), 4.5)
		self.assertEqual(CommonsManager.clamp(5, 4, 4.6), 4.6)
		self.assertEqual(CommonsManager.clamp(4, 4.4, 5), 4.4)
		self.assertEqual(CommonsManager.clamp(1, -2, -1), -1)


	def test_angleToCardinal(self):
		self.assertEqual(CommonsManager.angleToCardinal(0), 'north')
		self.assertEqual(CommonsManager.angleToCardinal(90), 'east')
		self.assertEqual(CommonsManager.angleToCardinal(180), 'south')
		self.assertEqual(CommonsManager.angleToCardinal(270), 'west')
		self.assertEqual(CommonsManager.angleToCardinal(45), 'north east')
		self.assertEqual(CommonsManager.angleToCardinal(135), 'south east')
		self.assertEqual(CommonsManager.angleToCardinal(225), 'south west')
		self.assertEqual(CommonsManager.angleToCardinal(315), 'north west')


	def test_isYes(self):
		class DialogSession(object):

			def __init__(self, slotsAsObjects: dict):
				self.slotsAsObjects = slotsAsObjects


		class Slot(object):

			def __init__(self, value):
				self.value = {'value': value}


		session1 = DialogSession(dict())
		session2 = DialogSession({
			'Answer': [
				Slot('yes')
			]
		})
		session3 = DialogSession({
			'Answer': [
				Slot('no')
			]
		})
		session4 = DialogSession({
			'Answer': [
				Slot('yeah')
			]
		})

		self.assertFalse(CommonsManager.isYes(session1))
		self.assertTrue(CommonsManager.isYes(session2))
		self.assertFalse(CommonsManager.isYes(session3))
		self.assertFalse(CommonsManager.isYes(session4))


	def test_indexOf(self):
		string1 = 'unittest'
		string2 = 'unit test'
		string3 = 'unnittest'
		string4 = 'test'

		self.assertEqual(CommonsManager.indexOf('unittest', string1), 0)
		self.assertEqual(CommonsManager.indexOf('unittest', string2), -1)
		self.assertEqual(CommonsManager.indexOf('unittest', string3), -1)
		self.assertEqual(CommonsManager.indexOf('unit', string4), -1)
		self.assertEqual(CommonsManager.indexOf('test', string1), 4)
		self.assertEqual(CommonsManager.indexOf('nn', string3), 1)


	def test_isUuid(self):
		validStrings = [
			'6e9bb2f8-bedb-4ade-9db7-f455e4c03051',
			'{6e9bb2f8-bedb-4ade-9db7-f455e4c03051}',
			'6e9bb2f8-becb-4ade-9db7-f455e4c03051',
			'6e9bb2f8bedb4ade9db7f455e4c03051',
			'urn:uuid:6e9bb2f8bedb4ade9db7f455e4c03051'
		]
		invalidStrings = [
			'{6e9bb2f8-begb-4ade-9db7-f455e4c03051}',
			'6e9bb2f8-bedb-4ade-9db7-f455e4c030',
			'unittests'
		]

		for string in validStrings:
			try:
				val = UUID(string)
			except:
				val = None

			self.assertIsNotNone(val)


		for string in invalidStrings:
			try:
				val = UUID(string)
			except:
				val = None

			self.assertIsNone(val)


if __name__ == '__main__':
	unittest.main()
