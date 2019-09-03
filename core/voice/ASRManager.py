import time
import uuid
from pathlib import Path

import core.base.Managers as managers
from core.base.Manager import Manager
from core.commons import commons
from core.dialog.model.DialogSession import DialogSession
from core.voice.model import ASR
from core.voice.model.SnipsASR import SnipsASR

try:
	# noinspection PyUnresolvedReferences
	from core.voice.model.GoogleASR import GoogleASR
except ImportError:
	pass

from core.base.model.Intent import Intent

class ASRManager(Manager):

	NAME = 'ASRManager'

	def __init__(self, mainClass):
		super().__init__(mainClass, self.NAME)
		managers.ASRManager = self

		self._asr = SnipsASR()
		if managers.ConfigManager.getAliceConfigByName(configName='asr').lower() == 'google' and not managers.ConfigManager.getAliceConfigByName('keepASROffline') and not managers.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
			self._asr = GoogleASR()

			managers.SnipsServicesManager.runCmd('stop', ['snips-asr'])
			self._logger.info('[{}] Turned Snips ASR off'.format(self.name))
		else:
			managers.SnipsServicesManager.runCmd('start', ['snips-asr'])
			self._logger.info('[{}] Started Snips ASR'.format(self.name))


	@property
	def asr(self) -> ASR:
		return self._asr


	def onInternetConnected(self, *args):
		if not managers.ConfigManager.getAliceConfigByName('keepASROffline'):
			asr = managers.ConfigManager.getAliceConfigByName('asr').lower()
			if asr != 'snips' and not managers.ConfigManager.getAliceConfigByName('keepASROffline') and not managers.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
				self._logger.info('[{}] Connected to internet, switching ASR'.format(self.name))
				managers.SnipsServicesManager.runCmd('stop', ['snips-asr'])
				if asr == 'google':
					self._asr = GoogleASR()
				managers.ThreadManager.doLater(interval=3, func=managers.MqttServer.say, args=[managers.TalkManager.randomTalk('internetBack', module='AliceCore'), 'all'])


	def onInternetLost(self, *args):
		if not isinstance(self._asr, SnipsASR):
			self._logger.info('[{}] Internet lost, switching to snips ASR'.format(self.name))
			managers.SnipsServicesManager.runCmd('start', ['snips-asr'])
			self._asr = SnipsASR()
			managers.ThreadManager.doLater(interval=3, func=managers.MqttServer.say, args=[managers.TalkManager.randomTalk('internetLost', module='AliceCore'), 'all'])


	def onStartListening(self, session: DialogSession):
		if isinstance(self._asr, SnipsASR):
			return
		else:
			start = time.time()
			result = self._asr.onListen()
			end = time.time()
			processing = float(end - start)

			if result:
				# Stop listener as fast as possible
				managers.MqttServer.publish(topic='hermes/asr/stopListening', payload={'sessionId': session.sessionId, 'siteId': session.siteId})

				result = managers.LanguageManager.sanitizeNluQuery(result)
				self._logger.debug('[{}] - {} output: "{}"'.format(self.NAME, self._asr.__class__.__name__, result))

				inheritedIntentFilter = session.intentFilter if session.intentFilter else None

				if not inheritedIntentFilter:
					intentFilter = [intent.justTopic for intent in managers.ModuleManager.supportedIntents if isinstance(intent, Intent) and not intent.protected]
				else:
					intentFilter = [intent.justTopic for intent in inheritedIntentFilter if isinstance(intent, Intent) and not intent.protected]

				# Add Global Intents
				intentFilter.append(Intent('GlobalStop').justTopic)

				managers.MqttServer.publish(topic='hermes/asr/textCaptured', payload={'sessionId': session.sessionId, 'text': result, 'siteId': session.siteId, 'likelihood': 1, 'seconds': processing})

				managers.MqttServer.publish(topic='hermes/nlu/query', payload={'id':session.sessionId, 'input': result, 'intentFilter': intentFilter, 'sessionId': session.sessionId})
			else:
				managers.MqttServer.publish(topic='hermes/nlu/intentNotRecognized')
				managers.MqttServer.playSound(
					soundFile=Path(commons.rootDir(), 'assistant/custom_dialogue/sound/error.wav'),
					sessionId=uuid.uuid4(),
					absolutePath=True,
					siteId=session.siteId
				)
