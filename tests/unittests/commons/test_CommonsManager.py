import unittest
from unittest import mock

from core.commons.CommonsManager import CommonsManager
from core.commons import constants

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
			'second')


	def test_payload(self):
		class MQTTMessage:
			def __init__(self, payload):
				self.payload = payload

		self.assertEqual(
			CommonsManager.payload(MQTTMessage("{'test': 2}")),
			dict())
		self.assertEqual(
			CommonsManager.payload(MQTTMessage(None)),
			dict())
		self.assertEqual(
			CommonsManager.payload(MQTTMessage(b'\x81')),
			dict())
		self.assertEqual(
			CommonsManager.payload(MQTTMessage('{"test": 2}')),
			{'test': 2})
		self.assertEqual(
			CommonsManager.payload(MQTTMessage(b'{"test": 2}')),
			{'test': 2})
		self.assertEqual(
			CommonsManager.payload(MQTTMessage('true')),
			{'true': True})
		self.assertEqual(
			CommonsManager.payload(MQTTMessage('false')),
			{'false': False})
		self.assertEqual(
			CommonsManager.payload(MQTTMessage(b'true')),
			{'true': True})


	def test_parseSlotsToObjects(self):
		class MQTTMessage:
			def __init__(self, payload):
				self.payload = payload

		self.assertEqual(
			CommonsManager.parseSlotsToObjects(MQTTMessage(None)),
			dict())
		#TODO more tests required


	def test_parseSlots(self):
		class MQTTMessage:
			def __init__(self, payload):
				self.payload = payload

		self.assertEqual(
			CommonsManager.parseSlots(MQTTMessage(None)),
			dict())
		message = MQTTMessage('{"slots": [\
			{"slotName": "slotName1", "rawValue": "rawValue1"},\
			{"slotName": "slotName2", "rawValue": "rawValue2"}]}')
		self.assertEqual(
			CommonsManager.parseSlots(message),
			{"slotName1": "rawValue1", "slotName2": "rawValue2"})


	def test_parseSessionId(self):
		class MQTTMessage:
			def __init__(self, payload):
				self.payload = payload

		self.assertEqual(
			CommonsManager.parseSessionId(MQTTMessage(None)),
			False)
		self.assertEqual(
			CommonsManager.parseSessionId(MQTTMessage('{"sessionId": "sessionIdValue"}')),
			"sessionIdValue")


	def test_parseCustomData(self):
		class MQTTMessage:
			def __init__(self, payload):
				self.payload = payload

		self.assertEqual(
			CommonsManager.parseCustomData(MQTTMessage(None)),
			dict())
		self.assertEqual(
			CommonsManager.parseCustomData(MQTTMessage(b'{"customData": "nonJsonString"}')),
			dict())
		self.assertEqual(
			CommonsManager.parseCustomData(MQTTMessage(b'{"customData": null}')),
			dict())
		self.assertEqual(
			CommonsManager.parseCustomData(MQTTMessage('{"customData": "{\\"test\\": \\"test\\"}"}')),
			{'test': 'test'})


	def test_parseSiteId(self):
		class MQTTMessage:
			def __init__(self, payload):
				self.payload = payload

		self.assertEqual(
			CommonsManager.parseSiteId(MQTTMessage('{"siteId": "site_id", "IPAddress": "127.0.0.1"}')),
			'site id')
		self.assertEqual(
			CommonsManager.parseSiteId(MQTTMessage('{"IPAddress": "127.0.0.1"}')),
			'127.0.0.1')
		self.assertEqual(
			CommonsManager.parseSiteId(MQTTMessage('{}')),
			constants.DEFAULT_SITE_ID)


	def test_getDuration(self):
		"""Test getDuration method"""

		class DialogSession:
			def __init__(self, slotsAsObjects: dict):
				self.slotsAsObjects = slotsAsObjects

		class TimeObject:
			def __init__(self, value: dict, entity: str = 'snips/duration'):
				self.value = value
				self.entity = entity

		timeDict = {
			'seconds': 6,
			'minutes': 5,
			'hours': 4,
			'days': 3,
			'weeks': 2,
			'months': 1
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


if __name__ == "__main__":
	unittest.main()
