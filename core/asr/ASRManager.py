from pathlib import Path
from typing import Dict

import paho.mqtt.client as mqtt

from core.asr.model import ASR
from core.asr.model.ASRResult import ASRResult
from core.asr.model.Recorder import Recorder
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


	def onStart(self):
		super().onStart()
		self._startASREngine()


	def onStop(self):
		if self._asr:
			self._asr.onStop()


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

		if not self._asr.checkDependencies():
			if not self._asr.install():
				self._asr = None

		if self._asr is None:
			self.logWarning('ASR did not satisfy the user settings, falling back to pocketsphinx')
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
			self._startASREngine()


	def onInternetLost(self):
		if self._asr.isOnlineASR:
			self.logInfo('Internet lost, switching to offline ASR')
			self._asr.onStop()
			self._startASREngine()


	def onStartListening(self, session: DialogSession):
		self._asr.onStartListening(session)
		self.ThreadManager.newThread(name=f'streamdecode_{session.siteId}', target=self.decodeStream, args=[session])


	def decodeStream(self, session: DialogSession):
		result: ASRResult = self._asr.decodeStream(session)

		if result and result.text:
			self.MqttManager.publish(topic=constants.TOPIC_ASR_STOP_LISTENING, payload={'sessionId': session.sessionId, 'siteId': session.siteId})
			self.logDebug(f'ASR captured: {result.text}')
			text = self.LanguageManager.sanitizeNluQuery(result.text)

			supportedIntents = result.session.intentFilter or self.SkillManager.supportedIntents
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


	def onAudioFrame(self, message: mqtt.MQTTMessage, siteId: str):
		if siteId not in self._streams or not self._streams[siteId].isRecording:
			return

		self._streams[siteId].onAudioFrame(message)


	def onSessionError(self, session: DialogSession):
		if session.siteId not in self._streams or not self._streams[session.siteId].isRecording:
			return

		self._streams[session.siteId].onSessionError(session)


	def addRecorder(self, siteId: str, recorder: Recorder):
		self._streams[siteId] = recorder
