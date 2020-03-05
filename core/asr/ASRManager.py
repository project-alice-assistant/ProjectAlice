from importlib import import_module, reload
from pathlib import Path
from typing import Dict

import paho.mqtt.client as mqtt

from core.asr.model import ASR
from core.asr.model.ASRResult import ASRResult
from core.asr.model.Recorder import Recorder
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
			package = 'core.asr.model.GoogleASR'
		elif userASR == 'deepspeech':
			package = 'core.asr.model.DeepSpeechASR'
		else:
			package = 'core.asr.model.PocketSphinxASR'

		module = import_module(package)
		asr = getattr(module, package.rsplit('.', 1)[-1])
		self._asr = asr()

		if not self._asr.checkDependencies():
			if not self._asr.install():
				self._asr = None
			else:
				module = reload(module)
				asr = getattr(module, package.rsplit('.', 1)[-1])
				self._asr = asr()

		if self._asr is None:
			self.logFatal("Couldn't install ASR, going down")
			return

		if self._asr.isOnlineASR and (not online or keepASROffline or stayOffline):
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


	def onPartialTextCaptured(self, session: DialogSession, text: str, likelihood: float, seconds: float):
		self.logDebug(f'Captured {text} with a likelihood of {likelihood}')


	def decodeStream(self, session: DialogSession):
		result: ASRResult = self._asr.decodeStream(session)

		if result and result.text:
			self.MqttManager.publish(topic=constants.TOPIC_ASR_STOP_LISTENING, payload={'sessionId': session.sessionId, 'siteId': session.siteId})

			if session.hasEnded:
				return

			self.logDebug(f'ASR captured: {result.text}')
			text = self.LanguageManager.sanitizeNluQuery(result.text)

			self.MqttManager.publish(topic=constants.TOPIC_TEXT_CAPTURED, payload={'sessionId': session.sessionId, 'text': text, 'siteId': session.siteId, 'likelihood': result.likelihood, 'seconds': result.processingTime})
		else:
			if session.hasEnded:
				return

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
		self._streams.pop(session.siteId, None)


	def onSessionEnded(self, session: DialogSession):
		if not self._asr or session.siteId not in self._streams or not self._streams[session.siteId].isRecording:
			return

		self._asr.end(session)
		self._streams.pop(session.siteId, None)


	def onVadUp(self, siteId: str):
		if not self._asr or siteId not in self._streams or not self._streams[siteId].isRecording:
			return

		self._asr.onVadUp()


	def onVadDown(self, siteId: str):
		if not self._asr or siteId not in self._streams or not self._streams[siteId].isRecording:
			return

		self._asr.onVadDown()


	def addRecorder(self, siteId: str, recorder: Recorder):
		self._streams[siteId] = recorder
