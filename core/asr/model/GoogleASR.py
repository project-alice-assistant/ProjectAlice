from pathlib import Path

import os
from google.cloud import speech
from google.cloud.speech import enums, types

from core.asr.model.ASR import ASR
from core.base.SuperManager import SuperManager
from core.voice.model.MicrophoneStream import MicrophoneStream


# noinspection PyUnresolvedReferences
class GoogleASR(ASR):

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
		self._streamingConfig = types.StreamingRecognitionConfig(config=self._config, single_utterance=True, interim_results=False)


	@staticmethod
	def _listen(responses):
		for response in responses:
			if not response.results:
				continue

			result = response.results[0]
			if not result.alternatives:
				continue

			# Display the transcription of the top alternative.
			transcript = result.alternatives[0].transcript

			if result.is_final:
				return transcript


	def onListen(self) -> str:
		micSampleRate = SuperManager.getInstance().configManager.getAliceConfigByName('micSampleRate')

		with MicrophoneStream(int(micSampleRate), int(micSampleRate / 10)) as stream:
			audio_generator = stream.generator()
			requests = (types.StreamingRecognizeRequest(audio_content=content) for content in audio_generator)
			responses = self._client.streaming_recognize(self._streamingConfig, requests)
			result = self._listen(responses)

		return result
