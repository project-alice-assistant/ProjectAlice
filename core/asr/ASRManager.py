from core.asr.model import ASR
from core.asr.model.SnipsASR import SnipsASR
from core.base.model.Intent import Intent
from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.util.Stopwatch import Stopwatch


class ASRManager(Manager):
	NAME = 'ASRManager'

	def __init__(self):
		super().__init__(self.NAME)
		self._asr = None


	def onStart(self):
		super().onStart()

		if self.ConfigManager.getAliceConfigByName(configName='asr').lower() == 'google' and not self.ConfigManager.getAliceConfigByName('keepASROffline') and not self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
			# noinspection PyUnresolvedReferences
			from core.asr.model.GoogleASR import GoogleASR

			self._asr = GoogleASR()
		else:
			from core.asr.model.PocketSphinxASR import PocketSphinxASR
			self._asr = PocketSphinxASR()
			self.logInfo('Started PocketSphinx ASR')


	@property
	def asr(self) -> ASR:
		return self._asr


	def onInternetConnected(self):
		if not self.ConfigManager.getAliceConfigByName('keepASROffline'):
			asr = self.ConfigManager.getAliceConfigByName('asr').lower()
			if asr != 'snips' and not self.ConfigManager.getAliceConfigByName('keepASROffline') and not self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
				self.logInfo('Connected to internet, switching ASR')
				self.SnipsServicesManager.runCmd('stop', ['snips-asr'])
				if asr == 'google':
					# TODO needs better handling. A header import with some checks if needed or not
					# noinspection PyUnresolvedReferences
					from core.asr.model.GoogleASR import GoogleASR

					self._asr = GoogleASR()


	def onInternetLost(self):
		if not isinstance(self._asr, SnipsASR):
			self.logInfo('Internet lost, switching to offline ASR')
			self.SnipsServicesManager.runCmd('start', ['snips-asr'])
			self._asr = SnipsASR()


	def onStartListening(self, session: DialogSession, *args, **kwargs):
		if isinstance(self._asr, SnipsASR):
			return

		with Stopwatch() as processingTime:
			result = self._asr.onListen()
			print(result)

		if result:
			# Stop listener as fast as possible
			self.MqttManager.publish(topic=constants.TOPIC_STOP_LISTENING, payload={'sessionId': session.sessionId, 'siteId': session.siteId})

			result = self.LanguageManager.sanitizeNluQuery(result)
			self.logDebug(f'{self._asr.__class__.__name__} output: "{result}"')

			supportedIntents = session.intentFilter or self.SkillManager.supportedIntents
			intentFilter = [intent.justTopic for intent in supportedIntents if isinstance(intent, Intent) and not intent.isProtected]

			self.MqttManager.publish(topic=constants.TOPIC_TEXT_CAPTURED, payload={'sessionId': session.sessionId, 'text': result, 'siteId': session.siteId, 'likelihood': 1, 'seconds': processingTime})

			self.MqttManager.publish(topic=constants.TOPIC_NLU_QUERY, payload={'id': session.sessionId, 'input': result, 'intentFilter': intentFilter, 'sessionId': session.sessionId})
		else:
			self.MqttManager.publish(topic=constants.TOPIC_INTENT_NOT_RECOGNIZED)
			self.MqttManager.playSound(
				soundFilename='error',
				location='assistant/custom_dialogue/sound',
				siteId=session.siteId
			)
