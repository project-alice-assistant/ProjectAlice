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
import time
import wave
from pathlib import Path
from threading import Event
from typing import Optional

from core.asr.model.ASRResult import ASRResult
from core.asr.model.Asr import Asr
from core.asr.model.Recorder import Recorder
from core.dialog.model.DialogSession import DialogSession
from core.util.Stopwatch import Stopwatch


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
		self._isStreamAble = False
		self._apiUrl = ''
		self._headers = dict()
		self._wav: Optional[wave.Wave_write] = None
		self._recording: Event = Event()


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('azureRegion') or not self.ConfigManager.getAliceConfigByName('azureKey'):
			raise Exception('Please provide Azure Key and Region in settings')
		self._apiUrl = f'https://{self.ConfigManager.getAliceConfigByName("azureRegion")}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language={self.LanguageManager.getLanguageAndCountryCode()}&profanity=raw&format=detailed'
		self._headers = {
			'Accept': 'application/json;text/xml',
		    'Content-Type': 'audio/wav; codecs=audio/pcm; samplerate=16000',
		    'Ocp-Apim-Subscription-Key': self.ConfigManager.getAliceConfigByName('azureKey'),
		    #'Transfer-Encoding': 'chunked',
		    'Expect': '100-continue'
		}


	def onStartListening(self, session: DialogSession):
		self._wav = wave.open(str(Path('var/asrCapture.wav')), 'wb')
		self._wav.setsampwidth(2)
		self._wav.setframerate(self.AudioServer.SAMPLERATE)
		self._wav.setnchannels(1)


	def recordFrame(self, frame: bytes):
		if not self._wav or not self._recorder or not self._recorder.isRecording:
			return
		self._wav.writeframes(frame)


	def onVadUp(self, **kwargs):
		if self._recorder and not self._recording:
			self._recording = True


	def onVadDown(self, **kwargs):
		if self._recording:
			self._wav.close()
			self.end()


	def decodeStream(self, session: DialogSession) -> Optional[ASRResult]:
		super().decodeStream(session)
		recorder = Recorder(self._timeout, session.user, session.deviceUid)
		self.ASRManager.addRecorder(session.deviceUid, recorder)
		self._recorder = recorder
		self._recorder.startRecording()
		self._recording = False

		with Stopwatch() as processingTime:
			while self._recorder.isRecording:
				time.sleep(0.1)

			result = None
			try:
				response = requests.post(url=self._apiUrl, data=Path('var/asrCapture.wav').read_bytes(), headers=self._headers)
				result = json.loads(response.text)
			except Exception as e:
				self.logWarning(f'Failed ASR request: {e}')

		return ASRResult(
			text=result['NBest'][0]['ITN'],
			session=session,
			likelihood=result['NBest'][0]['Confidence'],
			processingTime=processingTime.time
		) if result else None
