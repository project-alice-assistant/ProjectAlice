from pathlib import Path
from typing import Optional

import os
from google.cloud.speech import SpeechClient, enums, types

from core.asr.model.ASR import ASR
from core.asr.model.ASRResult import ASRResult
from core.asr.model.Recorder import Recorder
from core.util.Stopwatch import Stopwatch


class GoogleASR(ASR):
	NAME = 'Google ASR'


	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = True

		self._client: Optional[SpeechClient] = None
		self._streamingConfig: Optional[types.StreamingRecognitionConfig] = None


	def onStart(self):
		super().onStart()
		os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(Path(self.Commons.rootDir(), 'credentials/googlecredentials.json'))

		# noinspection PyUnresolvedReferences
		config = types.RecognitionConfig(
			encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
			sample_rate_hertz=self.ConfigManager.getAliceConfigByName('micSampleRate'),
			language_code=self.LanguageManager.activeLanguageAndCountryCode
		)

		self._client = SpeechClient()
		self._streamingConfig = types.StreamingRecognitionConfig(config=config)


	def decodeStream(self, recorder: Recorder) -> ASRResult:
		super().decodeStream(recorder)

		responses = None
		with Stopwatch() as processingTime:
			while recorder.isRecording:
				# noinspection PyUnresolvedReferences
				for chunk in recorder.generator():
					if self._timeout.isSet():
						break

					requests = types.StreamingRecognizeRequest(audio_content=chunk)

				try:
					responses = self._client.streaming_recognize(self._streamingConfig, requests)
				except RuntimeError as e:
					self.logWarning(f'Decoding failed: {e}')
					break

			self.end(recorder)

		result = self._checkResponses(responses)

		return ASRResult(
			text=result[0],
			session=recorder.session,
			likelihood=result[1],
			processingTime=processingTime.time
		) if result else None


	@staticmethod
	def _checkResponses(responses: dict) -> Optional[tuple]:
		if responses is None:
			return None

		for response in responses:
			if not response.results:
				continue

			result = response.result[0]
			if not result.alternatives:
				continue

			if result.is_final:
				transcript = result.alternatives[0].transcript
				confidence = result.alternatives[0].confidence
				return transcript, confidence

		return None
