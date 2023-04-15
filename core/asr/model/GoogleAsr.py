#  Copyright (c) 2021
#
#  This file, GoogleAsr.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:45 CEST

import os
from pathlib import Path
from threading import Event
from typing import Iterable, Optional

from core.asr.model.ASRResult import ASRResult
from core.asr.model.Asr import Asr
from core.asr.model.Recorder import Recorder
from core.dialog.model.DialogSession import DialogSession
from core.util.Stopwatch import Stopwatch


try:
	# noinspection PyUnresolvedReferences,PyPackageRequirements
	from google.cloud.speech import SpeechClient, enums, types
except:
	pass  # Auto installed


# noinspection PyAbstractClass
class GoogleAsr(Asr):
	NAME = 'Google Asr'
	DEPENDENCIES = {
		'system': [],
		'pip'   : {
			'grpcio==1.44.0 --no-binary=grpcio',
			'grpcio-status==1.44.0 --no-binary=grpcio-status',
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

		self._internetLostFlag = Event()  # Set if internet goes down, cut the decoding
		self._lastResultCheck = 0  # The time the intermediate results were last checked. If actual time is greater than this value + 3, stop processing, internet issues


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

		recorder = Recorder(self._timeout, session.user, session.deviceUid)
		self.ASRManager.addRecorder(session.deviceUid, recorder)
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
				except Exception as e:
					self._internetLostFlag.clear()
					self.logWarning(f'Failed ASR request: {e}')

			self.end()

		return ASRResult(
			text=result[0],
			session=session,
			likelihood=result[1],
			processingTime=processingTime.time
		) if result else None


	def onInternetLost(self):
		self._internetLostFlag.set()


	def _checkResponses(self, session: DialogSession, responses: Iterable) -> Optional[tuple]:
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
			else:
				self.partialTextCaptured(session=session, text=result.alternatives[0].transcript, likelihood=result.alternatives[0].confidence, seconds=0)

		return None


	def updateCredentials(self):
		Path(self.Commons.rootDir(), 'credentials/googlecredentials.json').write_text(
			self.ConfigManager.getAliceConfigByName('googleASRCredentials'))

		self.ASRManager.onStop()
		self.ASRManager.onStart()
