#  Copyright (c) 2021
#
#  This file, test_TalkManager.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:52 CEST

import unittest
from unittest import mock
from unittest.mock import MagicMock, PropertyMock

from core.voice.TalkManager import TalkManager


class TestTalkManager(unittest.TestCase):

	@mock.patch('core.voice.TalkManager.TalkManager.Commons', new_callable=PropertyMock)
	def test_chooseTalk(self, mock_commons):
		common_mock = MagicMock()
		common_mock.getFunctionCaller.return_value = 'TalkManager'
		mock_commons.return_value = common_mock

		talkManager = TalkManager()

		# when short and default version exist
		talkManager._langData = {
			'skill': {
				'de': {
					'talk': {
						'short': ['shortString'],
						'default': ['defaultString']
					}
				}
			}
		}
		self.assertEqual(talkManager.chooseTalk('talk', 'skill', 'de', 'en', False), 'defaultString')
		self.assertEqual(talkManager.chooseTalk('talk', 'skill', 'de', 'en', True), 'shortString')


		# when only default version exists
		talkManager._langData = {
			'skill': {
				'de': {
					'talk': {
						'default': ['defaultString']
					}
				}
			}
		}
		self.assertEqual(talkManager.chooseTalk('talk', 'skill', 'de', 'en', True), 'defaultString')


		# when list instead of dict is used
		talkManager._langData = {
			'skill': {
				'de': {
					'talk': ['defaultString']
				}
			}
		}
		self.assertEqual(talkManager.chooseTalk('talk', 'skill', 'de', 'en', True), 'defaultString')


		# when only fallback language exists
		talkManager._langData = {
			'skill': {
				'en': {
					'talk': ['defaultString']
				}
			}
		}
		self.assertEqual(talkManager.chooseTalk('talk', 'skill', 'de', 'en', True), 'defaultString')


		# when required keys do not exist in active and fallback language
		talkManager._langData = {'skill': {'en': {}}}
		self.assertEqual(talkManager.chooseTalk('talk', 'skill', 'de', 'en', True), '')

		talkManager._langData = {'skill': {'de': {}}}
		self.assertEqual(talkManager.chooseTalk('talk', 'skill', 'de', 'en', True), '')

		talkManager._langData = {'skill': {}}
		self.assertEqual(talkManager.chooseTalk('talk', 'skill', 'de', 'en', True), '')

		talkManager._langData = {}
		self.assertEqual(talkManager.chooseTalk('talk', 'skill', 'de', 'en', True), '')


if __name__ == "__main__":
	unittest.main()
