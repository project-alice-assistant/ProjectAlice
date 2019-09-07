import json
import time

import os
import random
import shutil
from random import randint

from core.ProjectAliceExceptions import ModuleStartingFailed
from core.base.SuperManager import SuperManager
from core.base.model.Intent import Intent
from core.base.model.Module import Module
from core.commons import commons
from core.dialog.model.DialogSession import DialogSession


class RedQueen(Module):
	_INTENT_WHO_ARE_YOU = Intent('WhoAreYou')
	_INTENT_GOOD_MORNING = Intent('GoodMorning', isProtected=True)
	_INTENT_GOOD_NIGHT = Intent('GoodNight', isProtected=True)
	_INTENT_CHANGE_USER_STATE = Intent('ChangeUserState')


	def __init__(self):
		self._SUPPORTED_INTENTS = [
			self._INTENT_WHO_ARE_YOU,
			self._INTENT_GOOD_MORNING,
			self._INTENT_GOOD_NIGHT,
			self._INTENT_CHANGE_USER_STATE
		]

		self._redQueen = None

		super().__init__(self._SUPPORTED_INTENTS)


	def onStart(self):
		redQueenIdentityFile = self._getRedQueenIdentityFileName()
		redQueenIdentityFileTemplate = redQueenIdentityFile + '.dist'

		if not os.path.isfile(redQueenIdentityFile):
			if os.path.isfile(redQueenIdentityFileTemplate):
				shutil.copyfile(redQueenIdentityFileTemplate, redQueenIdentityFile)
				self._logger.info('[{}] New Red Queen is born'.format(self.name))

				with open(self._getRedQueenIdentityFileName(), 'r') as f:
					self._redQueen = json.load(f)

				self._redQueen['infos']['born'] = time.strftime("%d.%m.%Y")
				self._saveRedQueenIdentity()
			else:
				self._logger.info('[{}] Cannot find Red Queen identity template'.format(self.name))
				raise ModuleStartingFailed(moduleName=self.name)
		else:
			self._logger.info('[{}] Found existing Red Queen identity'.format(self.name))
			with open(self._getRedQueenIdentityFileName(), 'r') as f:
				self._redQueen = json.load(f)

		return super().onStart()


	def onStop(self):
		self._saveRedQueenIdentity()
		super().onStop()


	def onBooted(self):
		self._decideStateOfMind()
		if self.getConfig('randomSpeaking'):
			self.randomlySpeak(init=True)


	def onSleep(self):
		SuperManager.getInstance().userManager.sleeping()


	def onWakeup(self):
		SuperManager.getInstance().userManager.wakeup()


	@property
	def mood(self) -> str:
		return self._redQueen['infos']['mood']


	@staticmethod
	def _getRedQueenIdentityFileName() -> str:
		return os.path.dirname(__file__) + '/redQueen.json'


	def _saveRedQueenIdentity(self):
		with open(self._getRedQueenIdentityFileName(), 'w') as f:
			json.dump(self._redQueen, f, indent=4, sort_keys=False)


	def onQuarterHour(self):
		if not SuperManager.getInstance().userManager.checkIfAllUser('sleeping'):
			self.changeRedQueenStat('tiredness', 1)
			self.changeRedQueenStat('boredom', 2)
			self.changeRedQueenStat('happiness', -1)
		else:
			self.changeRedQueenStat('tiredness', -2)
			self.changeRedQueenStat('boredom', -2)
			self.changeRedQueenStat('happiness', 1)
			self.changeRedQueenStat('anger', -2)
			self.changeRedQueenStat('frustration', -2)


	def onFiveMinute(self):
		self._redQueen['infos']['mood'] = self._decideStateOfMind()
		self._saveRedQueenIdentity()


	def onSessionEnded(self, session: DialogSession):
		if 'input' not in session.payload:
			return

		self.changeRedQueenStat('boredom', -2)
		self.changeRedQueenStat('frustration', -1)

		beenPolite = self.politnessUsed(session.payload['input'])
		if beenPolite:
			self.changeRedQueenStat('happiness', 4)
			self.changeRedQueenStat('anger', -4)
			self.changeRedQueenStat('frustration', -2)

			if self.mood == 'Anger':
				chance = 85
			elif self.mood == 'Tiredness':
				chance = 20
			elif self.mood == 'Boredom':
				chance = 50
			elif self.mood == 'Frustration':
				chance = 10
			else:
				chance = 25

			if randint(0, 100) < chance:
				self.say(text=self.randomTalk('thanksForBeingNice'), siteId=session.siteId)
				return

			return


	def politnessUsed(self, text: str) -> bool:
		forms = SuperManager.getInstance().languageManager.getStrings(key='politness', module=self.name)

		for form in forms:
			if form not in text:
				continue

			return True

		return False


	def onUserCancel(self, session: DialogSession):
		self.changeRedQueenStat('frustration', 2)


	def inTheMood(self, session: DialogSession) -> bool:
		if self.getConfig(key='disableMoodTraits'):
			return True

		if self.mood == 'Anger':
			chance = 40
		elif self.mood == 'Tiredness':
			chance = 20
		elif self.mood == 'Boredom':
			chance = 10
		elif self.mood == 'Frustration':
			chance = 15
		else:
			chance = 2

		if not SuperManager.getInstance().protectedIntentManager.isProtectedIntent(session.message.topic) and not self.politnessUsed(session.payload['input']) and random.randint(0, 100) < chance and not SuperManager.getInstance().multiIntentManager.isProcessing(session.sessionId):
			self.endDialog(session.sessionId, self.randomTalk('noInTheMood'))
			return False

		return True


	def onMessage(self, intent: str, session: DialogSession) -> bool:
		if not self.filterIntent(intent, session):
			return False

		if intent == self._INTENT_CHANGE_USER_STATE:
			slots = session.slotsAsObjects
			if 'State' not in slots.keys():
				self._logger.error('[{}] No state provided for changing user state'.format(self.name))
				self.endDialog(sessionId=session.sessionId,
											text=SuperManager.getInstance().talkManager.randomTalk('error', module='system'),
											siteId=session.siteId)
				return True

			if 'Who' in slots.keys():
				pass
			else:
				try:
					SuperManager.getInstance().moduleManager.broadcast(slots['State'][0].value['value'])
				except:
					self._logger.warning('[{}] Unsupported user state "{}"'.format(self.name, slots['State'][0].value['value']))

			self.endDialog(sessionId=session.sessionId,
										text=SuperManager.getInstance().talkManager.randomTalk(slots['State'][0].value['value']),
										siteId=session.siteId)

		elif intent == self._INTENT_GOOD_NIGHT:
			self.endDialog(sessionId=session.sessionId,
										text=self.randomTalk('goodNight'),
										siteId=session.siteId)

			SuperManager.getInstance().moduleManager.broadcast('onSleep')

		elif intent == self._INTENT_GOOD_MORNING:
			SuperManager.getInstance().moduleManager.broadcast('onWakeup')
			time.sleep(0.5)
			self.endDialog(sessionId=session.sessionId,
										text=self.randomTalk('goodMorning'),
										siteId=session.siteId)

		elif intent == self._INTENT_WHO_ARE_YOU:
			self.endDialog(sessionId=session.sessionId,
										text=self.randomTalk('aliceInfos'),
										siteId=session.siteId)

		return True


	def randomlySpeak(self, init: bool = False):
		mini = self.getConfig('randomTalkMinDelay')
		maxi = self.getConfig('randomTalkMaxDelay')

		if self.mood == 'Anger':
			maxi /= 3
		elif self.mood == 'Tiredness' or self.mood == 'Boredom':
			mini /= 2
			maxi /= 2
		elif self.mood == 'Frustrated':
			maxi /= 2

		rnd = random.randint(mini, maxi)
		SuperManager.getInstance().threadManager.doLater(interval=rnd, func=self.randomlySpeak)
		self._logger.info('[{}] Scheduled next random speaking in {} seconds'.format(self.name, rnd))

		if not init and not SuperManager.getInstance().userManager.checkIfAllUser('goingBed') and not SuperManager.getInstance().userManager.checkIfAllUser('sleeping'):
			self.say(self.randomTalk('randomlySpeak{}'.format(self.mood)), siteId='all')


	def changeRedQueenStat(self, stat: str, amount: int):
		if stat not in self._redQueen['stats'].keys():
			self._logger.warning('[{}] Asked to change stat {} but it does not exist'.format(self.name, stat))

		self._redQueen['stats'][stat] += amount
		if self._redQueen['stats'][stat] < 0:
			self._redQueen['stats'][stat] = 0
		elif self._redQueen['stats'][stat] > 100:
			self._redQueen['stats'][stat] = 100


	def _decideStateOfMind(self) -> str:
		# TODO Algorythm for weighting the 5 stats
		stats = {
			'Anger'      : self._redQueen['stats']['anger'] * 5,
			'Tiredness'  : self._redQueen['stats']['tiredness'] * 4,
			'Happiness'  : self._redQueen['stats']['happiness'] * 3,
			'Frustration': self._redQueen['stats']['frustration'] * 2,
			'Boredom'    : self._redQueen['stats']['boredom']
		}

		return commons.dictMaxValue(stats)
