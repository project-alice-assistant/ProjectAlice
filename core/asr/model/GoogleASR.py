from pathlib import Path
from typing import Optional

import os

from core.asr.model.ASR import ASR
from core.asr.model.ASRResult import ASRResult
from core.asr.model.Recorder import Recorder
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession

try:
	from google.cloud.speech import SpeechClient, enums, types
except:
	pass


class GoogleASR(ASR):
	NAME = 'Google ASR'
	DEPENDENCIES = [
		'google-cloud-speech==1.3.1'
	]


	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = True

		self._client: Optional[SpeechClient] = None
		self._streamingConfig: Optional[types.StreamingRecognitionConfig] = None


	def onStart(self):
		super().onStart()
		os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(Path(self.Commons.rootDir(), 'credentials/googlecredentials.json'))

		self._client = SpeechClient()
		# noinspection PyUnresolvedReferences
		config = types.RecognitionConfig(
			encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
			sample_rate_hertz=self.ConfigManager.getAliceConfigByName('micSampleRate'),
			language_code=self.LanguageManager.activeLanguageAndCountryCode
		)

		self._streamingConfig = types.StreamingRecognitionConfig(config=config, interim_results=True)


	def install(self) -> bool:
		if not super().install():
			return False


	def decodeStream(self, session: DialogSession) -> Optional[ASRResult]:
		super().decodeStream(session)
		recorder = Recorder(self._timeout)
		self.ASRManager.addRecorder(session.siteId, recorder)
		with recorder as stream:
			audioStream = stream.audioStream()
			requests = (types.StreamingRecognizeRequest(audio_content=content) for content in audioStream)
			responses = self._client.streaming_recognize(self._streamingConfig, requests)
			result = self._checkResponses(responses)

		self.end(recorder, session)

		return ASRResult(
			text=result[0],
			session=session,
			likelihood=result[1],
			processingTime=10
		) if result else None


	def _checkResponses(self, responses) -> Optional[tuple]:
		if responses is None:
			return None

		for response in responses:
			if not response.results:
				continue

			result = response.results[0]
			if not result.alternatives:
				continue

			if result.is_final:
				return result.alternatives[0].transcript, result.alternatives[0].confidence
			else:
				self.broadcast(method=constants.EVENT_ASR_INTERMEDIATE_RESULT, exceptions=[constants.DUMMY], propagateToSkills=True, result=result.alternatives[0].transcript)

		return None
