import time
import uuid
from pathlib import Path

from core.base.Manager import Manager
from core.base.SuperManager import SuperManager
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

	def __init__(self):
		super().__init__(self.NAME)
		self._asr = None


	def onStart(self):
		super().onStart()

		if SuperManager.getInstance().configManager.getAliceConfigByName(configName='asr').lower() == 'google' and not SuperManager.getInstance().configManager.getAliceConfigByName('keepASROffline') and not SuperManager.getInstance().configManager.getAliceConfigByName('stayCompletlyOffline'):
			self._asr = GoogleASR()
			SuperManager.getInstance().snipsServicesManager.runCmd('stop', ['snips-asr'])
			self._logger.info('[{}] Turned Snips ASR off'.format(self.name))
		else:
			self._asr = SnipsASR()
			SuperManager.getInstance().snipsServicesManager.runCmd('start', ['snips-asr'])
			self._logger.info('[{}] Started Snips ASR'.format(self.name))


	@property
	def asr(self) -> ASR:
		return self._asr


	def onInternetConnected(self, *args):
		if not SuperManager.getInstance().configManager.getAliceConfigByName('keepASROffline'):
			asr = SuperManager.getInstance().configManager.getAliceConfigByName('asr').lower()
			if asr != 'snips' and not SuperManager.getInstance().configManager.getAliceConfigByName('keepASROffline') and not SuperManager.getInstance().configManager.getAliceConfigByName('stayCompletlyOffline'):
				self._logger.info('[{}] Connected to internet, switching ASR'.format(self.name))
				SuperManager.getInstance().snipsServicesManager.runCmd('stop', ['snips-asr'])
				if asr == 'google':
					self._asr = GoogleASR()
				SuperManager.getInstance().threadManager.doLater(interval=3, func=SuperManager.getInstance().mqttManager.say, args=[SuperManager.getInstance().talkManager.randomTalk('internetBack', module='AliceCore'), 'all'])


	def onInternetLost(self, *args):
		if not isinstance(self._asr, SnipsASR):
			self._logger.info('[{}] Internet lost, switching to snips ASR'.format(self.name))
			SuperManager.getInstance().snipsServicesManager.runCmd('start', ['snips-asr'])
			self._asr = SnipsASR()
			SuperManager.getInstance().threadManager.doLater(interval=3, func=SuperManager.getInstance().mqttManager.say, args=[SuperManager.getInstance().talkManager.randomTalk('internetLost', module='AliceCore'), 'all'])


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
				SuperManager.getInstance().mqttManager.publish(topic='hermes/asr/stopListening', payload={'sessionId': session.sessionId, 'siteId': session.siteId})

				result = SuperManager.getInstance().languageManager.sanitizeNluQuery(result)
				self._logger.debug('[{}] - {} output: "{}"'.format(self.NAME, self._asr.__class__.__name__, result))

				supportedIntents = session.intentFilter or SuperManager.getInstance().moduleManager.supportedIntents
				intentFilter = [intent.justTopic for intent in supportedIntents if isinstance(intent, Intent) and not intent.protected]

				# Add Global Intents
				intentFilter.append(Intent('GlobalStop').justTopic)

				SuperManager.getInstance().mqttManager.publish(topic='hermes/asr/textCaptured', payload={'sessionId': session.sessionId, 'text': result, 'siteId': session.siteId, 'likelihood': 1, 'seconds': processing})

				SuperManager.getInstance().mqttManager.publish(topic='hermes/nlu/query', payload={'id':session.sessionId, 'input': result, 'intentFilter': intentFilter, 'sessionId': session.sessionId})
			else:
				SuperManager.getInstance().mqttManager.publish(topic='hermes/nlu/intentNotRecognized')
				SuperManager.getInstance().mqttManager.playSound(
					soundFile=Path(commons.rootDir(), 'assistant/custom_dialogue/sound/error.wav'),
					sessionId=uuid.uuid4(),
					absolutePath=True,
					siteId=session.siteId
				)
