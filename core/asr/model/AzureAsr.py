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
import json
import requests
import wave
from pathlib import Path
from typing import Optional

from core.asr.model.ASRResult import ASRResult
from core.asr.model.Asr import Asr
from core.asr.model.Recorder import Recorder
from core.dialog.model.DialogSession import DialogSession
from core.util.Stopwatch import Stopwatch


#https://github.com/Azure-Samples/cognitive-services-speech-sdk/blob/master/samples/python/console/speech_sample.py
try:
	# noinspection PyUnresolvedReferences,PyPackageRequirements
	import azure.cognitiveservices.speech as speechSdk
except:
	pass  # Auto installed


# noinspection PyAbstractClass
class AzureAsr(Asr):
	NAME = 'Azure Asr'
	DEPENDENCIES = {
		'system': [],
		'pip'   : {}
	}


	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = True
		self._speechConfig = None
		self._speechRecognizer = None
		self._stream = None
		self._audioConfig = None


		self._apiUrl = ''
		self._headers = dict()
		self._wav: Optional[wave.Wave_write] = None
		self._triggerFlag = self.ThreadManager.newEvent('asrTriggerFlag')


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('azureRegion') or not self.ConfigManager.getAliceConfigByName('azureKey'):
			raise Exception('Please provide Azure Key and Region in settings')

		self._stream = speechSdk.audio.PushAudioInputStream()
		self._audioConfig = speechSdk.audio.AudioConfig(stream = self._stream)
		self._speechConfig = speechSdk.SpeechConfig(subscription=self.ConfigManager.getAliceConfigByName('azureKey'), region=self.ConfigManager.getAliceConfigByName('azureRegion'))
		self._speechRecognizer = speechSdk.SpeechRecognizer(speech_config = self._speechConfig, audio_config = self._audioConfig)


		# self._apiUrl = f'https://{self.ConfigManager.getAliceConfigByName("azureRegion")}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language={self.LanguageManager.getLanguageAndCountryCode()}&profanity=raw&format=detailed'
		# self._headers = {
		# 	'Accept': 'application/json;text/xml',
		#     'Content-Type': 'audio/wav; codecs=audio/pcm; samplerate=16000',
		#     'Ocp-Apim-Subscription-Key': self.ConfigManager.getAliceConfigByName('azureKey'),
		#     #'Transfer-Encoding': 'chunked',
		#     'Expect': '100-continue'
		# }


	def recordFrame(self, frame: bytes):
		if not self._wav:
			return
		self._wav.writeframes(frame)


	def onVadUp(self):
		self._triggerFlag.set()


	def onVadDown(self):
		if not self._triggerFlag.is_set():
			return

		self._recorder.stopRecording()


	def decodeStream(self, session: DialogSession) -> Optional[ASRResult]:
		super().decodeStream(session)
		result = None
		previous = ''

		with Stopwatch() as processingTime:
			tmpWav = Path('/tmp/asrCapture.wav')
			wav = wave.open(str(tmpWav), 'wb')
			wav.setsampwidth(2)
			wav.setframerate(self.AudioServer.SAMPLERATE)
			wav.setnchannels(1)

			with Recorder(self._timeout, session.user, session.deviceUid) as recorder:
				self.ASRManager.addRecorder(session.deviceUid, recorder)
				self._recorder = recorder

				for chunk in recorder:
					print('chunk')
					if not chunk:
						break

					wav.writeframes(chunk)

					try:
						response = requests.post(url=self._apiUrl, data=tmpWav.read_bytes(), headers=self._headers)

						try:
							result = json.loads(response.text)
						except:
							continue
					except Exception as e:
						self.logWarning(f'Failed ASR request: {e}')

					if result and 'NBest' in result and result['NBest'][0]['ITN'] != previous:
						previous = result['NBest'][0]['ITN']
						self.partialTextCaptured(session=session, text=result, likelihood=result['NBest'][0]['Confidence'], seconds=processingTime.time)

			self._triggerFlag.clear()
			self.end()

		return ASRResult(
			text=result['NBest'][0]['ITN'],
			session=session,
			likelihood=result['NBest'][0]['Confidence'],
			processingTime=processingTime.time
		) if result and 'NBest' in result else None
