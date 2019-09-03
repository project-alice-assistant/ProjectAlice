import json
import time

import os
import random
import shutil
from random import randint

import core.base.Managers    as managers
from core.ProjectAliceExceptions import ModuleStartingFailed
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
		managers.UserManager.sleeping()


	def onWakeup(self):
		managers.UserManager.wakeup()


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
		if not managers.UserManager.checkIfAllUser('sleeping'):
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
				managers.MqttServer.say(text=self.randomTalk('thanksForBeingNice'), client=session.siteId)
				return

			return


	def politnessUsed(self, text: str) -> bool:
		forms = managers.LanguageManager.getStrings(key='politness', module=self.name)

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

		if not managers.ProtectedIntentManager.isProtectedIntent(session.message.topic) and not self.politnessUsed(session.payload['input']) and random.randint(0, 100) < chance and not managers.MultiIntentManager.isProcessing(session.sessionId):
			managers.MqttServer.endTalk(session.sessionId, self.randomTalk('noInTheMood'))
			return False

		return True


	def onMessage(self, intent: str, session: DialogSession) -> bool:
		if not self.filterIntent(intent, session):
			return False

		if intent == self._INTENT_CHANGE_USER_STATE:
			slots = session.slotsAsObjects
			if 'State' not in slots.keys():
				self._logger.error('[{}] No state provided for changing user state'.format(self.name))
				managers.MqttServer.endTalk(sessionId=session.sessionId,
											text=managers.TalkManager.randomTalk('error', module='system'),
											client=session.siteId)
				return True

			if 'Who' in slots.keys():
				pass
			else:
				try:
					managers.ModuleManager.broadcast(slots['State'][0].value['value'])
				except:
					self._logger.warning('[{}] Unsupported user state "{}"'.format(self.name, slots['State'][0].value['value']))

			managers.MqttServer.endTalk(sessionId=session.sessionId,
										text=managers.TalkManager.randomTalk(slots['State'][0].value['value']),
										client=session.siteId)

		elif intent == self._INTENT_GOOD_NIGHT:
			managers.MqttServer.endTalk(sessionId=session.sessionId,
										text=self.randomTalk('goodNight'),
										client=session.siteId)
			managers.ModuleManager.broadcast('onSleep')

		elif intent == self._INTENT_GOOD_MORNING:
			managers.ModuleManager.broadcast('onWakeup')
			time.sleep(0.5)
			managers.MqttServer.endTalk(sessionId=session.sessionId,
										text=self.randomTalk('goodMorning'),
										client=session.siteId)

		elif intent == self._INTENT_WHO_ARE_YOU:
			managers.MqttServer.endTalk(sessionId=session.sessionId,
										text=self.randomTalk('aliceInfos'),
										client=session.siteId)

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
		managers.ThreadManager.doLater(interval=rnd, func=self.randomlySpeak)
		self._logger.info('[{}] Scheduled next random speaking in {} seconds'.format(self.name, rnd))

		if not init and not managers.UserManager.checkIfAllUser('goingBed') and not managers.UserManager.checkIfAllUser('sleeping'):
			managers.MqttServer.say(self.randomTalk('randomlySpeak{}'.format(self.mood)), client='all')


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
