import re
import subprocess
from pathlib import Path

from google.oauth2.service_account import Credentials

from core.commons import commons
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.TTS import TTS
from core.voice.model.TTSEnum import TTSEnum

try:
	from google.cloud import texttospeech
except ModuleNotFoundError:
	subprocess.run(['pip3', 'install', 'google-cloud-texttospeech'])


class GoogleTTS(TTS):
	TTS = TTSEnum.GOOGLE

	def __init__(self, user: User = None):
		super().__init__(user)
		self._online = True
		self._privacyMalus = -20


		creds = Credentials.from_service_account_file(filename=Path(commons.rootDir(), 'credentials/googlecredentials.json'))
		self._client = texttospeech.TextToSpeechClient(credentials=creds)

		# TODO implement the others
		# https://cloud.google.com/text-to-speech/docs/voices
		self._supportedLangAndVoices = {
			'en-US': {
				'male': {
					'en-US-Standard-B': {
						'neural': False
					},
					'en-US-Standard-D': {
						'neural': False
					},
					'en-US-Wavenet-A': {
						'neural': True
					},
					'en-US-Wavenet-B': {
						'neural': True
					},
					'en-US-Wavenet-D': {
						'neural': True
					}
				},
				'female': {
					'en-US-Standard-C': {
						'neural': False
					},
					'en-US-Standard-E' : {
						'neural': False
					},
					'en-US-Wavenet-C': {
						'neural': True
					},
					'en-US-Wavenet-E' : {
						'neural': True
					},
					'en-US-Wavenet-F' : {
						'neural': True
					}
				}
			},
			'fr-FR': {
				'male'  : {
					'fr-FR-Standard-B': {
						'neural': False
					},
					'fr-FR-Standard-D': {
						'neural': False
					},
					'fr-FR-Wavenet-B' : {
						'neural': True
					},
					'fr-FR-Wavenet-D' : {
						'neural': True
					}
				},
				'female': {
					'fr-FR-Standard-A': {
						'neural': False
					},
					'fr-FR-Standard-C': {
						'neural': False
					},
					'fr-FR-Wavenet-A' : {
						'neural': True
					},
					'fr-FR-Wavenet-C' : {
						'neural': True
					}
				}
			},
			'de-DE': {
				'male'  : {
					'de-DE-Standard-B': {
						'neural': False
					},
					'de-DE-Wavenet-B' : {
						'neural': True
					},
					'de-DE-Wavenet-D' : {
						'neural': True
					}
				},
				'female': {
					'de-DE-Standard-A': {
						'neural': False
					},
					'de-DE-Wavenet-A' : {
						'neural': True
					},
					'de-DE-Wavenet-C' : {
						'neural': True
					}
				}
			}
		}


	@staticmethod
	def _checkText(session: DialogSession) -> str:
		text = session.payload['text']

		if not re.search('<speak>', text):
			text = '<speak>{}</speak>'.format(text)

		return text


	def onSay(self, session: DialogSession):
		super().onSay(session)

		if not self._text:
			return

		tmpFile = self.TEMP_ROOT / self._cacheFile.with_suffix('.mp3')
		if not self._cacheFile.exists():
			imput = texttospeech.types.module.SynthesisInput(ssml=self._text)
			audio = texttospeech.types.module.AudioConfig(
				audio_encoding=texttospeech.enums.AudioEncoding.MP3,
				sample_rate_hertz=22050
			)
			voice = texttospeech.types.module.VoiceSelectionParams(
				language_code=self._lang,
				name=self._voice
			)

			response = self._client.synthesize_speech(imput, voice, audio)
			if not response:
				self._logger.error('[{}] Failed downloading speech file'.format(self.TTS.value))
				return

			tmpFile.write_bytes(response['AudioStream'].read())

			self._mp3ToWave(src=tmpFile, dest=self._cacheFile)

		self._speak(self._cacheFile, session)
