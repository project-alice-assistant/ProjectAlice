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
		self._apiUrl = ''
		self._headers = dict()


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('azureRegion') or not self.ConfigManager.getAliceConfigByName('azureKey'):
			raise Exception('Please provide Azure Key and Region in settings')

		self._apiUrl = f'https://{self.ConfigManager.getAliceConfigByName("azureRegion")}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language={self.LanguageManager.getLanguageAndCountryCode()}&profanity=raw&format=detailed'
		self._headers = {
			'Accept': 'application/json;text/xml',
		    'Connection': 'Keep-Alive',
		    'Content-Type': 'audio/wav; codecs=audio/pcm; samplerate=16000',
		    'Ocp-Apim-Subscription-Key': self.ConfigManager.getAliceConfigByName('azureKey'),
		    'Transfer-Encoding': 'chunked',
		    'Expect': '100-continue'
		}


	def decodeStream(self, session: DialogSession) -> Optional[ASRResult]:
		super().decodeStream(session)

		recorder = Recorder(self._timeout, session.user, session.deviceUid)
		self.ASRManager.addRecorder(session.deviceUid, recorder)
		self._recorder = recorder
		result = None
		with Stopwatch() as processingTime:
			with recorder as stream:
				try:
					response = requests.post(url=self._apiUrl, data=stream.audioStream(), headers=self._headers)
					result = json.loads(response.text)
				except Exception as e:
					self.logWarning(f'Failed ASR request: {e}')

			self.end()

		return ASRResult(
			text=result['NBest'][0]['ITN'],
			session=session,
			likelihood=result['NBest'][0]['Confidence'],
			processingTime=processingTime.time
		) if result else None
