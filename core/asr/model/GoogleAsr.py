import os
from pathlib import Path
from threading import Event
from time import time
from typing import Generator, Optional

from core.asr.model.ASRResult import ASRResult
from core.asr.model.Asr import Asr
from core.asr.model.Recorder import Recorder
from core.dialog.model.DialogSession import DialogSession
from core.util.Stopwatch import Stopwatch

try:
	# noinspection PyUnresolvedReferences,PyPackageRequirements
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
		self._credentialsFile = Path(self.Commons.rootDir(), 'credentials/googlecredentials.json')
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = True

		self._client: Optional[SpeechClient] = None
		self._streamingConfig: Optional[types.StreamingRecognitionConfig] = None

		if self._credentialsFile.exists() and not self.ConfigManager.getAliceConfigByName('googleASRCredentials'):
			self.ConfigManager.updateAliceConfiguration(key='googleASRCredentials', value=self._credentialsFile.read_text(), doPreAndPostProcessing=False)

		self._internetLostFlag = Event() # Set if internet goes down, cut the decoding
		self._lastResultCheck = 0 # The time the intermediate results were last checked. If actual time is greater than this value + 3, stop processing, internet issues

		self._previousCapture = '' # The text that was last captured in the iteration


	def onStart(self):
		super().onStart()
		os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(self._credentialsFile)

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
		result = None
		with Stopwatch() as processingTime:
			with recorder as stream:
				audioStream = stream.audioStream()
				# noinspection PyUnresolvedReferences
				try:
					requests = (types.StreamingRecognizeRequest(audio_content=content) for content in audioStream)
					responses = self._client.streaming_recognize(self._streamingConfig, requests)
					result = self._checkResponses(session, responses)
				except:
					self._internetLostFlag.clear()
					self.logWarning('Failed ASR request')

			self.end()

		return ASRResult(
			text=result[0],
			session=session,
			likelihood=result[1],
			processingTime=processingTime.time
		) if result else None


	def onInternetLost(self):
		self._internetLostFlag.set()


	def _checkResponses(self, session: DialogSession, responses: Generator) -> Optional[tuple]:
		if responses is None:
			return None

		for response in responses:
			if self._internetLostFlag.is_set():
				self.logDebug('Internet connectivity lost during ASR decoding')

				if not response.results:
					raise Exception('Internet connectivity lost during decoding')

				result = response.results[0]
				return result.alternatives[0].transcript, result.alternatives[0].confidence

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
			elif result.alternatives[0].transcript == self._previousCapture:
				now = int(time())

				if self._lastResultCheck == 0:
					self._lastResultCheck = 0
					continue

				if now > self._lastResultCheck + 3:
					self.logDebug(f'Stopping process as there seems to be connectivity issues')
					return result.alternatives[0].transcript, result.alternatives[0].confidence

				self._lastResultCheck = now

		return None
