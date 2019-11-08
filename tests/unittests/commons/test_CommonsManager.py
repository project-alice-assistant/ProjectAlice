import unittest
from unittest import mock
from unittest.mock import MagicMock

from core.commons.CommonsManager import CommonsManager

class TestCommonsManager(unittest.TestCase):
	
	def test_getFunctionCaller(self):
		self.assertEqual(CommonsManager.getFunctionCaller(1), 'test_CommonsManager')

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


if __name__ == "__main__":
	unittest.main()
