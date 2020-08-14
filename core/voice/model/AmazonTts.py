import re

from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.TTSEnum import TTSEnum
from core.voice.model.Tts import Tts

try:
	import boto3
except ModuleNotFoundError:
	pass # Auto installeed


class AmazonTts(Tts):
	TTS = TTSEnum.AMAZON

	DEPENDENCIES = {
		'system': [],
		'pip'   : {
			'boto3==1.13.19'
		}
	}

	def __init__(self, user: User = None):
		super().__init__(user)
		self._online = True
		self._privacyMalus = -20
		self._client = None

		# TODO implement the others
		# https://docs.aws.amazon.com/polly/latest/dg/voicelist.html
		self._supportedLangAndVoices = {
			'arb': {
				'female': {
					'Zeina': {
						'neural': False
					}
				}
			},
			'cmn-CN': {
				'female': {
					'Zhiyu': {
						'neural': False
					}
				}
			},
			'da-DK': {
				'male': {
					'Mads': {
						'neural': False
					}
				},
				'female': {
					'Naja': {
						'neural': False
					}
				}
			},
			'nl-NL': {
				'male': {
					'Ruben': {
						'neural': False
					}
				},
				'female': {
					'Lotte': {
						'neural': False
					}
				}
			},
			'en-AU': {
				'male': {
					'Russell': {
						'neural': False
					}
				},
				'female': {
					'Nicole': {
						'neural': False
					}
				}
			},
			'en-GB': {
				'male': {
					'Brian': {
						'neural': True
					}
				},
				'female': {
					'Amy': {
						'neural': True
					},
					'Emma': {
						'neural': True
					}
				}
			},
			'en-IN': {
				'female': {
					'Aditi': {
						'neural': False
					},
					'Raveena': {
						'neural': False
					}
				}
			},
			'en-US': {
				'male': {
					'Joey': {
						'neural': True
					},
					'Justin': {
						'neural': True
					},
					'Matthew': {
						'neural': True
					},
				},
				'female': {
					'Ivy': {
						'neural': True
					},
					'Joanna': {
						'neural': True
					},
					'Kendra': {
						'neural': True
					},
					'Kimberly': {
						'neural': True
					},
					'Salli': {
						'neural': True
					}
				}
			},
			'en-GB-WLS': {
				'male': {
					'Geraint': {
						'neural': False
					}
				}
			},
			'fr-FR': {
				'male': {
					'Mathieu': {
						'neural': False
					}
				},
				'female': {
					'Celine': {
						'neural': False
					}
				}
			},
			'fr-CA': {
				'female': {
					'Chantal': {
						'neural': False
					}
				}
			},
			'de-DE': {
				'male': {
					'Hans': {
						'neural': False
					}
				},
				'female': {
					'Marlene': {
						'neural': False
					},
					'Vicki': {
						'neural': False
					}
				}
			},
			'it-IT': {
				'male'  : {
					'Giorgio': {
						'neural': False
					}
				},
				'female': {
					'Bianca': {
						'neural': False
					},
					'Carla'  : {
						'neural': False
					}
				}
			}
		}


	def onStart(self):
		super().onStart()
		self._client = boto3.client(
			'polly',
			region_name=self.ConfigManager.getAliceConfigByName('awsRegion'),
			aws_access_key_id=self.ConfigManager.getAliceConfigByName('awsAccessKey'),
			aws_secret_access_key=self.ConfigManager.getAliceConfigByName('awsSecretKey')
		)


	@staticmethod
	def getWhisperMarkup() -> tuple:
		return '<amazon:effect name="whispered">', '</amazon:effect>'


	@staticmethod
	def _checkText(session: DialogSession) -> str:
		text = session.payload['text']

		if not re.search('<speak>', text):
			text = f'<speak><amazon:auto-breaths>{text}</amazon:auto-breaths></speak>'

		return text


	def onSay(self, session: DialogSession):
		super().onSay(session)

		if not self._text:
			return

		tmpFile = self.TEMP_ROOT / self._cacheFile.with_suffix('.mp3')
		if not self._cacheFile.exists():
			response = self._client.synthesize_speech(
				Engine='standard',
				LanguageCode=self._lang,
				OutputFormat='mp3',
				SampleRate=str(self.AudioServer.SAMPLERATE),
				Text=self._text,
				TextType='ssml',
				VoiceId=self._voice.title()
			)

			if not response:
				self.logError(f'[{self.TTS.value}] Failed downloading speech file')
				return

			tmpFile.write_bytes(response['AudioStream'].read())

			self._mp3ToWave(src=tmpFile, dest=self._cacheFile)
			tmpFile.unlink()

			self.logDebug(f'Downloaded speech file **{self._cacheFile.stem}**')
		else:
			self.logDebug(f'Using existing cached file **{self._cacheFile.stem}**')

		self._speak(self._cacheFile, session)
