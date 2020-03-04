from pathlib import Path
from typing import Generator, Optional

import os

from core.asr.model.ASR import ASR
from core.asr.model.ASRResult import ASRResult
from core.asr.model.Recorder import Recorder
from core.dialog.model.DialogSession import DialogSession
from core.util.Stopwatch import Stopwatch

try:
	from google.cloud.speech import SpeechClient, enums, types
except:
	pass


class GoogleASR(ASR):
	NAME = 'Google ASR'
	DEPENDENCIES = {
		'system': [],
		'pip'   : {
			'google-cloud-speech==1.3.1'
		}
	}


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


	def decodeStream(self, session: DialogSession) -> Optional[ASRResult]:
		super().decodeStream(session)
		recorder = Recorder(self._timeout)
		self.ASRManager.addRecorder(session.siteId, recorder)
		self._recorder = recorder
		with Stopwatch() as processingTime:
			with recorder as stream:
				audioStream = stream.audioStream()
				requests = (types.StreamingRecognizeRequest(audio_content=content) for content in audioStream)
				responses = self._client.streaming_recognize(self._streamingConfig, requests)
				result = self._checkResponses(session, responses)

			self.end(session)

		return ASRResult(
			text=result[0],
			session=session,
			likelihood=result[1],
			processingTime=processingTime.time
		) if result else None


	def _checkResponses(self, session: DialogSession, responses: Generator) -> Optional[tuple]:
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
				self.partialTextCaptured(session=session, text=result.alternatives[0].transcript, likelihood=result.alternatives[0].confidence, seconds=0)

		return None
