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
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = True

		self._client: Optional[SpeechClient] = None
		self._streamingConfig: Optional[types.StreamingRecognitionConfig] = None

		self._internetLostFlag = Event()  # Set if internet goes down, cut the decoding
		self._lastResultCheck = 0  # The time the intermediate results were last checked. If actual time is greater than this value + 3, stop processing, internet issues

		self._previousCapture = ''  # The text that was last captured in the iteration
		self._delayedGoogleConfirmation = False  # set whether slow internet is detected or not

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
				self._lastResultCheck = 0
				self._delayedGoogleConfirmation = False
				# print(f'Text confirmed by Google')
				return result.alternatives[0].transcript, result.alternatives[0].confidence
			elif result.alternatives[0].transcript != self._previousCapture:
				self.partialTextCaptured(session=session, text=result.alternatives[0].transcript, likelihood=result.alternatives[0].confidence, seconds=0)
				# below function captures the "potential" full utterance not just one word from it
				if len(self._previousCapture) <= len(result.alternatives[0].transcript):
					self._previousCapture = result.alternatives[0].transcript
			elif result.alternatives[0].transcript == self._previousCapture:

				# If we are here it's cause google hasn't responded yet with confirmation on captured text
				# Store the time in seconds since epoch
				now = int(time())
				# Set a reference to nows time plus 3 seconds
				self._lastResultCheck = now + 3
				# wait 3 seconds and see if google responds
				if not self._delayedGoogleConfirmation:
					# print(f'Text of "{self._previousCapture}" captured but not confirmed by GoogleASR yet')
					while now <= self._lastResultCheck:
						now = int(time())
						self._delayedGoogleConfirmation = True
					# Give google the option to still process  the utterance
					continue
				# During next iteration, If google hasn't responded in 3 seconds assume intent is correct
				if self._delayedGoogleConfirmation:
					self.logDebug(f'Stopping process as there seems to be connectivity issues')
					self._lastResultCheck = 0
					self._delayedGoogleConfirmation = False
					return result.alternatives[0].transcript, result.alternatives[0].confidence

		return None

