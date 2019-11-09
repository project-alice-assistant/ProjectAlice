import unittest
from unittest import mock
from unittest.mock import MagicMock

from core.commons.CommonsManager import CommonsManager

class TestCommonsManager(unittest.TestCase):
	
	def test_getFunctionCaller(self):
		self.assertEqual(CommonsManager.getFunctionCaller(1), 'test_CommonsManager')


	@mock.patch('core.commons.CommonsManager.CommonsManager.LanguageManager')
	def test_isEqualTranslated(self, mock_LanguageManager):
		commonsManager = CommonsManager()
		mock_LanguageManager.getStrings.return_value = ['String1', ' strIng2']
		self.assertTrue(commonsManager.isEqualTranslated('string1', 'compareTo', 'module'))
		mock_LanguageManager.getStrings.called_once_with('compareTo', 'module')
		self.assertTrue(commonsManager.isEqualTranslated('string2 ', 'compareTo', 'module'))
		self.assertFalse(commonsManager.isEqualTranslated('string3', 'compareTo', 'module'))


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
			{'true': 'true'})
		self.assertEqual(
			CommonsManager.payload(MQTTMessage('false')),
			{'false': 'false'})
		self.assertEqual(
			CommonsManager.payload(MQTTMessage(b'true')),
			{'true': 'true'})
		

	def test_toPascalCase(self):
		"""Test whether string gets correctly converted to pascal case"""
		self.assertEqual(CommonsManager.toPascalCase('example string'), 'ExampleString')
		self.assertEqual(CommonsManager.toPascalCase('Example-string_2', replaceSepCharacters=True), 'ExampleString2')
		self.assertEqual(CommonsManager.toPascalCase('Example+string/2', replaceSepCharacters=True, sepCharacters=('+', '/')), 'ExampleString2')


	def test_toCamelCase(self):
		"""Test whether string gets correctly converted to camel case"""
		self.assertEqual(CommonsManager.toCamelCase('example string'), 'exampleString')
		self.assertEqual(CommonsManager.toCamelCase('Example-string_2', replaceSepCharacters=True), 'exampleString2')
		self.assertEqual(CommonsManager.toCamelCase('Example+string/2', replaceSepCharacters=True, sepCharacters=('+', '/')), 'exampleString2')


	def test_isSpelledWord(self):
		"""Test whether string is spelled"""
		self.assertTrue(CommonsManager.isSpelledWord('e x a m p l e'))
		self.assertFalse(CommonsManager.isSpelledWord('example'))
		self.assertFalse(CommonsManager.isSpelledWord('e x am p l e'))


	def test_getDuration(self):
		"""Test getDuration method"""

		class DialogSession:
			def __init__(self, retVal: dict):
				self.retVal = retVal
			@property
			def slotsAsObjects(self) -> dict:
				return self.retVal

		class TimeObject:
			def __init__(self, retVal: dict, entity: str = 'snips/duration'):
				self.retVal = retVal
				self._entity = entity
			@property
			def entity(self) -> str:
				return self._entity
			@property
			def value(self) -> dict:
				return self.retVal

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


	def test_clamp(self):
		self.assertEqual(CommonsManager.clamp(4.5, 4, 5), 4.5)
		self.assertEqual(CommonsManager.clamp(5, 4, 4.6), 4.6)
		self.assertEqual(CommonsManager.clamp(4, 4.4, 5), 4.4)
		self.assertEqual(CommonsManager.clamp(1, -2, -1), -1)


if __name__ == "__main__":
	unittest.main()
