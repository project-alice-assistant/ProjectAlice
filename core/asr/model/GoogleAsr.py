from pathlib import Path
from typing import Generator, Optional

import os

from core.asr.model.ASRResult import ASRResult
from core.asr.model.Asr import Asr
from core.asr.model.Recorder import Recorder
from core.dialog.model.DialogSession import DialogSession
from core.util.Stopwatch import Stopwatch

try:
	from google.cloud.speech import SpeechClient, enums, types
except:
	pass # Auto installed


# noinspection PyAbstractClass
class GoogleAsr(Asr):

	NAME = 'Google Asr'
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

		self._previousCapture = ''


	def onStart(self):
		super().onStart()
		os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(Path(self.Commons.rootDir(), 'credentials/googlecredentials.json'))

		self._client = SpeechClient()
		# noinspection PyUnresolvedReferences
		config = types.RecognitionConfig(
			encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
			sample_rate_hertz=self.AudioServer.SAMPLERATE,
			language_code=self.LanguageManager.getLanguageAndCountryCode()
		)

		self._streamingConfig = types.StreamingRecognitionConfig(config=config, interim_results=True)


	def decodeStream(self, session: DialogSession) -> Optional[ASRResult]:
		super().decodeStream(session)

		recorder = Recorder(self._timeout, session.user, session.siteId)
		self.ASRManager.addRecorder(session.siteId, recorder)
		self._recorder = recorder
		with Stopwatch() as processingTime:
			with recorder as stream:
				audioStream = stream.audioStream()
				# noinspection PyUnresolvedReferences
				try:
					requests = (types.StreamingRecognizeRequest(audio_content=content) for content in audioStream)
					responses = self._client.streaming_recognize(self._streamingConfig, requests)
					result = self._checkResponses(session, responses)
				except:
					self.logWarning('Failed ASR request')

			self.end()

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
			elif result.alternatives[0].transcript != self._previousCapture:
				self.partialTextCaptured(session=session, text=result.alternatives[0].transcript, likelihood=result.alternatives[0].confidence, seconds=0)
				self._previousCapture = result.alternatives[0].transcript

		return None
