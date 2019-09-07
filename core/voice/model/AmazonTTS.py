import subprocess

import re

from core.base.SuperManager import SuperManager
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.TTS import TTS
from core.voice.model.TTSEnum import TTSEnum

try:
	import boto3
except ModuleNotFoundError:
	subprocess.run(['pip3', 'install', 'boto3'])


class AmazonTTS(TTS):
	TTS = TTSEnum.AMAZON

	def __init__(self, user: User = None):
		super().__init__(user)
		self._online = True
		self._privacyMalus = -20
		self._client = boto3.client(
			'polly',
			region_name=SuperManager.getInstance().configManager.getAliceConfigByName('awsRegion'),
			aws_access_key_id=SuperManager.getInstance().configManager.getAliceConfigByName('awsAccessKey'),
			aws_secret_access_key=SuperManager.getInstance().configManager.getAliceConfigByName('awsSecretKey')
		)

		# TODO implement the others
		# https://docs.aws.amazon.com/polly/latest/dg/voicelist.html
		self._supportedLangAndVoices = {
			'arb': {
				'female': {
					'zeina': {
						'neural': False
					}
				}
			},
			'cmn-CN': {
				'female': {
					'zhiyu': {
						'neural': False
					}
				}
			},
			'da-DK': {
				'male': {
					'mads': {
						'neural': False
					}
				},
				'female': {
					'naja': {
						'neural': False
					}
				}
			},
			'nl-NL': {
				'male': {
					'ruben': {
						'neural': False
					}
				},
				'female': {
					'lotte': {
						'neural': False
					}
				}
			},
			'en-AU': {
				'male': {
					'russell': {
						'neural': False
					}
				},
				'female': {
					'nicole': {
						'neural': False
					}
				}
			},
			'en-GB': {
				'male': {
					'brian': {
						'neural': True
					}
				},
				'female': {
					'amy': {
						'neural': True
					},
					'emma': {
						'neural': True
					}
				}
			},
			'en-IN': {
				'female': {
					'aditi': {
						'neural': False
					},
					'raveena': {
						'neural': False
					}
				}
			},
			'en-US': {
				'male': {
					'joey': {
						'neural': True
					},
					'justin': {
						'neural': True
					},
					'matthew': {
						'neural': True
					},
				},
				'female': {
					'ivy': {
						'neural': True
					},
					'joanna': {
						'neural': True
					},
					'kendra': {
						'neural': True
					},
					'kimberly': {
						'neural': True
					},
					'salli': {
						'neural': True
					}
				}
			},
			'en-GB-WLS': {
				'male': {
					'geraint': {
						'neural': False
					}
				}
			},
			'fr-FR': {
				'male': {
					'mathieu': {
						'neural': False
					}
				},
				'female': {
					'celine': {
						'neural': False
					}
				}
			},
			'fr-CA': {
				'female': {
					'chantal': {
						'neural': False
					}
				}
			},
			'de-DE': {
				'male': {
					'hans': {
						'neural': False
					}
				},
				'female': {
					'marlene': {
						'neural': False
					},
					'vicki': {
						'neural': False
					}
				}
			}
		}


	@staticmethod
	def _checkText(session: DialogSession) -> str:
		text = session.payload['text']

		if not re.search('<speak>', text):
			text = '<speak><amazon:auto-breaths>{}</amazon:auto-breaths></speak>'.format(text)

		return text


	def onSay(self, session: DialogSession):
		super().onSay(session)

		if not self._text:
			return

		tmpFile = self.TEMP_ROOT / self._cacheFile.with_suffix('.mp3')
		if not self._cacheFile.is_file():
			response = self._client.synthesize_speech(
				Engine='standard',
				LanguageCode=self._lang,
				OutputFormat='mp3',
				SampleRate='22050',
				Text=self._text,
				TextType='ssml',
				VoiceId=self._voice.title()
			)

			if not response:
				self._logger.error('[{}] Failed downloading speech file'.format(self.TTS.value))
				return

			tmpFile.write_bytes(response['AudioStream'].read())

			self._mp3ToWave(src=tmpFile, dest=self._cacheFile)

		self._speak(self._cacheFile, session)
