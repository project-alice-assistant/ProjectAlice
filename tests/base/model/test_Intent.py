#  Copyright (c) 2021
#
#  This file, test_Intent.py, is part of Project Alice.
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

from unittest import TestCase

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from core.base.model.Intent import Intent
from core.user.model.AccessLevels import AccessLevel


class TestAliceSkill(TestCase):
	intent1 = Intent('unittest')
	intent2 = Intent('unittest', authLevel=AccessLevel.ADMIN)
	intent3 = Intent('tests/unittest', authLevel=AccessLevel.GUEST, userIntent=False)


	def test_topic(self):
		self.assertEqual(self.intent1.topic, 'hermes/intent/unittest')
		self.assertEqual(self.intent2.topic, 'hermes/intent/unittest')
		self.assertEqual(self.intent3.topic, 'tests/unittest')


	def test_auth_level(self):
		self.assertEqual(self.intent1.authLevel, AccessLevel.ZERO)
		self.assertEqual(self.intent2.authLevel, AccessLevel.ADMIN)
		self.assertEqual(self.intent3.authLevel, AccessLevel.GUEST)


	def test_just_topic(self):
		self.assertEqual(self.intent1.justTopic, 'unittest')
		self.assertEqual(self.intent3.justTopic, 'tests/unittest')
		self.assertEqual(self.intent3.justTopic, 'tests/unittest')


	@patch('core.base.SuperManager.SuperManager')
	def test_dialog_mapping(self, mock_superManager):
		def dummyCallable():
			pass


		@property
		def testProperty():
			return


		# mock SuperManager
		mock_instance = MagicMock()
		mock_superManager.getInstance.return_value = mock_instance
		mock_instance.CommonsManager.getFunctionCaller.return_value = 'unittest'

		dialogMapping1 = {
			'unittest': dummyCallable
		}
		dialogMapping2 = testProperty
		dialogMapping3 = 'unittest'
		dialogMapping4 = dummyCallable

		self.intent1.dialogMapping = dialogMapping1
		self.intent2.dialogMapping = dialogMapping2

		self.assertEqual(self.intent1.dialogMapping, {'unittest:unittest': dummyCallable})
		self.assertEqual(self.intent2.dialogMapping, dict())
		self.assertEqual(self.intent3.dialogMapping, dict())

		self.intent1.dialogMapping = dialogMapping3
		self.intent2.dialogMapping = dialogMapping4
		self.assertEqual(self.intent1.dialogMapping, dict())
		self.assertEqual(self.intent2.dialogMapping, dict())


	def test_add_dialog_mapping(self):
		def dummyCallable():
			pass


		self.intent1.addDialogMapping({'test': dummyCallable, 'unittest2': 'dummy'}, 'unit')

		self.assertEqual(self.intent1.dialogMapping, {'unit:test': dummyCallable})


	@patch('core.base.SuperManager.SuperManager')
	def test_get_mapping(self, mock_superManager):
		@dataclass
		class Session(object):
			currentState: str


		def dummyCallable():
			pass


		def fallback():
			pass


		# mock SuperManager
		mock_instance = MagicMock()
		mock_superManager.getInstance.return_value = mock_instance
		mock_instance.commonsManager.getFunctionCaller.return_value = 'unittest'

		self.intent2.fallbackFunction = fallback
		self.intent2.addDialogMapping({'test': dummyCallable, 'unittest2': 'dummy'}, 'unit')

		self.assertEqual(self.intent2.getMapping(Session('unit:test')), dummyCallable)
		self.assertEqual(self.intent2.getMapping(Session('unit:test2')), fallback)
