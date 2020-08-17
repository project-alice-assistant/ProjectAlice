from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.TTSEnum import TTSEnum
from core.voice.model.Tts import Tts

try:
	from ibm_watson import TextToSpeechV1
	from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
except ModuleNotFoundError:
	pass # Installed automagically through Tts Manager


class WatsonTts(Tts):
	TTS = TTSEnum.WATSON

	DEPENDENCIES = {
		'system': [],
		'pip'   : {
			'ibm-watson==4.4.0'
		}
	}

	def __init__(self, user: User = None):
		super().__init__(user)
		self._online = True
		self._privacyMalus = -20
		self._client = None

		# TODO implement the others
		# https://cloud.ibm.com/apidocs/text-to-speech?code=python#list-voices
		self._supportedLangAndVoices = {
			'en-US': {
				'male': {
					'en-US_HenryV3Voice': {
						'neural': True
					},
					'en-US_KevinV3Voice': {
						'neural': True
					},
					'en-US_MichaelVoice': {
						'neural': True
					},
					'en-US_MichaelV3Voice': {
						'neural': True
					}
				},
				'female': {
					'en-US_AllisonVoice': {
						'neural': True
					},
					'en-US_AllisonV3Voice': {
						'neural': True
					},
					'en-US_EmilyV3Voice': {
						'neural': True
					},
					'en-US_LisaVoice': {
						'neural': True
					},
					'en-US_LisaV3Voice': {
						'neural': True
					},
					'en-US_OliviaV3Voice': {
						'neural': True
					}
				}
			},
			'fr-FR': {
				'female': {
					'fr-FR_ReneeVoice': {
						'neural': True
					},
					'fr-FR_ReneeV3Voice': {
						'neural': True
					}
				}
			},
			'de-DE': {
				'male': {
					'de-DE_DieterVoice': {
						'neural': True
					},
					'de-DE_DieterV3Voice': {
						'neural': True
					}
				},
				'female': {
					'de-DE_BirgitVoice': {
						'neural': True
					},
					'de-DE_BirgitV3Voice': {
						'neural': True
					},
					'de-DE_ErikaV3Voice': {
						'neural': True
					}
				}
			},
			'it-IT': {
				'female': {
					'it-IT_FrancescaVoice' : {
						'neural': True
					},
					'it-IT_FrancescaV3Voice': {
						'neural': True
					}
				}
			}
		}


	def onStart(self):
		super().onStart()
		self._client = TextToSpeechV1(
			authenticator=IAMAuthenticator(self.ConfigManager.getAliceConfigByName('ibmCloudAPIKey'))
		)
		self._client.set_service_url(self.ConfigManager.getAliceConfigByName('ibmCloudAPIURL'))


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
			try:
				response = self._client.synthesize(
					text=self._text,
					accept='audio/mp3',
					voice=self._voice
				)
				data = response.result.content
			except:
				self.logError(f'[{self.TTS.value}] Failed downloading speech file')
				return

			tmpFile.write_bytes(data)

			self._mp3ToWave(src=tmpFile, dest=self._cacheFile)
			tmpFile.unlink()

			self.logDebug(f'Downloaded speech file **{self._cacheFile.stem}**')
		else:
			self.logDebug(f'Using existing cached file **{self._cacheFile.stem}**')

		self._speak(self._cacheFile, session)
