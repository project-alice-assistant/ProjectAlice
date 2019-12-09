import unittest

from core.voice.TalkManager import TalkManager

class TestTalkManager(unittest.TestCase):

	def test_chooseTalk(self):
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
