from pathlib import Path

import os
from google.cloud import speech
from google.cloud.speech import enums, types

from core.asr.model.ASR import ASR
from core.base.SuperManager import SuperManager


# noinspection PyUnresolvedReferences
class GoogleASR(ASR):
	NAME = 'Google ASR'


	def __init__(self):
		super().__init__()

		os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(Path(SuperManager.getInstance().commons.rootDir(), 'credentials/googlecredentials.json'))

		self._client = speech.SpeechClient()
		self._config = types.RecognitionConfig(
			encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
			sample_rate_hertz=SuperManager.getInstance().configManager.getAliceConfigByName('micSampleRate'),
			language_code=SuperManager.getInstance().languageManager.activeLanguageAndCountryCode
		)
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = True
