from pathlib import Path
from typing import Dict, List

import paho.mqtt.client as mqtt

from core.asr.model import ASR
from core.asr.model.ASRResult import ASRResult
from core.asr.model.Recorder import Recorder
from core.asr.model.SnipsASR import SnipsASR
from core.base.model.Intent import Intent
from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class ASRManager(Manager):
	NAME = 'ASRManager'


	def __init__(self):
		super().__init__(self.NAME)
		self._asr = None
		self._streams: Dict[str, Recorder] = dict()
		self._thresholds: Dict[str, List[float]] = dict()
		self._thresholdRecorder = Recorder()

	def onStart(self):
		super().onStart()
		self._startASREngine()
		self.MqttManager.mqttClient.subscribe(constants.TOPIC_AUDIO_FRAME.format('+'))


	def _startASREngine(self):
		userASR = self.ConfigManager.getAliceConfigByName(configName='asr').lower()
		keepASROffline = self.ConfigManager.getAliceConfigByName('keepASROffline')
		stayOffline = self.ConfigManager.getAliceConfigByName('stayCompletlyOffline')
		online = self.InternetManager.online

		self._asr = None

		if userASR == 'google':
			from core.asr.model.GoogleASR import GoogleASR

			self._asr = GoogleASR()
		elif userASR == 'pocketsphinx':
			from core.asr.model.PocketSphinxASR import PocketSphinxASR

			self._asr = PocketSphinxASR()

		if self._asr.isOnlineASR and (not online or keepASROffline or stayOffline):
			self._asr = None

		if self._asr is None:
			from core.asr.model.PocketSphinxASR import PocketSphinxASR

			self._asr = PocketSphinxASR()

		self._asr.onStart()


	@property
	def asr(self) -> ASR:
		return self._asr


	def onInternetConnected(self):
		if self.ConfigManager.getAliceConfigByName('stayCompletlyOffline') or self.ConfigManager.getAliceConfigByName('keepASROffline'):
			return

		if not self._asr.isOnlineASR:
			self.logInfo('Connected to internet, switching ASR')
			self._asr.onStop()
			if self.ConfigManager.getAliceConfigByName(configName='asr').lower() == 'google':
				# noinspection PyUnresolvedReferences
				from core.asr.model.GoogleASR import GoogleASR

				self._asr = GoogleASR()

			self._asr.onStart()


	def onInternetLost(self):
		if self._asr.isOnlineASR:
			self.logInfo('Internet lost, switching to offline ASR')
			self._asr.onStop()
			self._startASREngine()


	def onStartListening(self, session: DialogSession, *args, **kwargs):
		if isinstance(self._asr, SnipsASR):
			return

		recorder = Recorder(session)
		self._streams[session.siteId] = recorder
		recorder.onStartListening(session)


	def onAudioFrame(self, message: mqtt.MQTTMessage, siteId: str):
		# If we are not trying to capture what a user is saying, we update the noise level threshold, constantly.
		# This allows for dynamic threshold even in noisy environements
		# if siteId not in self._streams or not self._streams[siteId].isListening:
		# 	self._thresholdRecorder.onAudioFrame(message)
		# else:
		# 	self._streams[siteId].onAudioFrame(message)

		if siteId not in self._streams or not self._streams[siteId].isListening:
			return

		self._streams[siteId].onAudioFrame(message)


	def onSessionError(self, session: DialogSession):
		if session.siteId not in self._streams or not self._streams[session.siteId].isListening:
			return

		self._streams[session.siteId].onSessionError(session)


	def onRecorded(self, session: DialogSession):
		if session.siteId not in self._streams:
			self.logInfo(f'Text was captured on site id "{session.siteId}" but there is not recorder associated')
			return

		self.MqttManager.publish(topic=constants.TOPIC_STOP_LISTENING, payload={'sessionId': session.sessionId, 'siteId': session.siteId})

		recorder = self._streams[session.siteId]
		result: ASRResult = self._asr.decode(recorder.getSamplePath(), session)

		if result:
			self.logInfo(f'ASR capture: {result.text}')
			text = self.LanguageManager.sanitizeNluQuery(result.text)

			supportedIntents = session.intentFilter or self.SkillManager.supportedIntents
			intentFilter = [intent.justTopic for intent in supportedIntents if isinstance(intent, Intent) and not intent.isProtected]

			self.MqttManager.publish(topic=constants.TOPIC_TEXT_CAPTURED, payload={'sessionId': session.sessionId, 'text': text, 'siteId': session.siteId, 'likelihood': result.likelihood, 'seconds': result.processingTime})
			self.MqttManager.publish(topic=constants.TOPIC_NLU_QUERY, payload={'id': session.sessionId, 'input': text, 'intentFilter': intentFilter, 'sessionId': session.sessionId})
		else:
			self.MqttManager.publish(topic=constants.TOPIC_INTENT_NOT_RECOGNIZED)
			self.MqttManager.playSound(
				soundFilename='error',
				location=Path('assistant/custom_dialogue/sound'),
				siteId=session.siteId
			)

		self._streams.pop(session.siteId, None)
