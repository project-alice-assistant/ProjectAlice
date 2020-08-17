from pathlib import Path

from google.oauth2.service_account import Credentials

from core.base.SuperManager import SuperManager
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.TTSEnum import TTSEnum
from core.voice.model.Tts import Tts

try:
	from google.cloud import texttospeech
except ModuleNotFoundError:
	pass # Auto installed


class GoogleTts(Tts):
	TTS = TTSEnum.GOOGLE

	DEPENDENCIES = {
		'system': [],
		'pip'   : {
			'google-cloud-texttospeech==1.0.1'
		}
	}

	def __init__(self, user: User = None):
		super().__init__(user)
		self._online = True
		self._privacyMalus = -20
		self._client = None

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
					'en-US-Standard-E': {
						'neural': False
					},
					'en-US-Wavenet-C': {
						'neural': True
					},
					'en-US-Wavenet-E': {
						'neural': True
					},
					'en-US-Wavenet-F': {
						'neural': True
					}
				}
			},
			'fr-FR': {
				'male': {
					'fr-FR-Standard-B': {
						'neural': False
					},
					'fr-FR-Standard-D': {
						'neural': False
					},
					'fr-FR-Wavenet-B': {
						'neural': True
					},
					'fr-FR-Wavenet-D': {
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
					'fr-FR-Wavenet-A': {
						'neural': True
					},
					'fr-FR-Wavenet-C': {
						'neural': True
					}
				}
			},
			'de-DE': {
				'male': {
					'de-DE-Standard-B': {
						'neural': False
					},
					'de-DE-Wavenet-B': {
						'neural': True
					},
					'de-DE-Wavenet-D': {
						'neural': True
					}
				},
				'female': {
					'de-DE-Standard-A': {
						'neural': False
					},
					'de-DE-Wavenet-A': {
						'neural': True
					},
					'de-DE-Wavenet-C': {
						'neural': True
					}
				}
			},
			'it-IT': {
				'male'  : {
					'it-IT-Standard-C': {
						'neural': False
					},
					'it-IT-Standard-D' : {
						'neural': False
					},
					'it-IT-Wavenet-C' : {
						'neural': True
					},
					'it-IT-Wavenet-D': {
						'neural': True
					}
				},
				'female': {
					'it-IT-Standard-A': {
						'neural': False
					},
					'it-IT-Standard-B' : {
						'neural': False
					},
					'it-IT-Wavenet-A' : {
						'neural': True
					},
					'it-IT-Wavenet-B': {
						'neural': True
					}
				}
			}
		}


	def onStart(self):
		super().onStart()
		self._client = texttospeech.TextToSpeechClient(
			credentials=Credentials.from_service_account_file(filename=Path(SuperManager.getInstance().commons.rootDir(), 'credentials/googlecredentials.json'))
		)


	@staticmethod
	def _checkText(session: DialogSession) -> str:
		text = session.payload['text']

		if not '<speak>' in text:
			text = f'<speak>{text}</speak>'

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
				sample_rate_hertz=self.AudioServer.SAMPLERATE
			)
			voice = texttospeech.types.module.VoiceSelectionParams(
				language_code=self._lang,
				name=self._voice
			)

			response = self._client.synthesize_speech(imput, voice, audio)
			if not response:
				self.logError(f'[{self.TTS.value}] Failed downloading speech file')
				return

			tmpFile.write_bytes(response.audio_content)

			self._mp3ToWave(src=tmpFile, dest=self._cacheFile)
			tmpFile.unlink()
			self.logDebug(f'Downloaded speech file **{self._cacheFile.stem}**')
		else:
			self.logDebug(f'Using existing cached file **{self._cacheFile.stem}**')

		self._speak(self._cacheFile, session)
