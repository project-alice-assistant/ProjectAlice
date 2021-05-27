#  Copyright (c) 2021
#
#  This file, AmazonTts.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:48 CEST

import re

from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.TTSEnum import TTSEnum
from core.voice.model.Tts import Tts

try:
	# noinspection PyUnresolvedReferences
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
		self._supportsSSML = False if self.ConfigManager.getAliceConfigByName('ttsNeural') and self._neuralVoice else True

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
					'Carla' : {
						'neural': False
					}
				}
			},
			'pl-PL': {
				'male'  : {
					'Jacek': {
						'neural': False
					},
					'Jan'  : {
						'neural': False
					}
				},
				'female': {
					'Ewa' : {
						'neural': False
					},
					'Maja': {
						'neural': False
					}
				}
			},
			'pt-BR': {
				'male'  : {
					'Ricardo': {
						'neural': False
					}
				},
				'female': {
					'Camila' : {
						'neural': False
					},
					'Vitoria': {
						'neural': False
					}
				}
			},
			'pt-PT': {
				'male'  : {
					'Cristiano': {
						'neural': False
					}
				},
				'female': {
					'Ines': {
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


	def _checkText(self, session: DialogSession) -> str:
		text = super()._checkText(session)

		if self._supportsSSML and not re.search('<amazon:auto-breaths>', text):
			text = re.sub(r'<speak>(.*)</speak>', r'<speak><amazon:auto-breaths>\1</amazon:auto-breaths></speak>', text)

		return text


	def onSay(self, session: DialogSession):
		super().onSay(session)

		if not self._text:
			return

		neural = self.ConfigManager.getAliceConfigByName('ttsNeural') and self._neuralVoice

		tmpFile = self.TEMP_ROOT / self._cacheFile.with_suffix('.mp3')
		if not self._cacheFile.exists():
			self.logDebug(f'Downloading file **{self._cacheFile.stem}**')
			response = self._client.synthesize_speech(
				Engine='neural' if neural else 'standard',
				LanguageCode=self._lang,
				OutputFormat='mp3',
				SampleRate=str(self.AudioServer.SAMPLERATE),
				Text=self._checkText(session) if neural else self._text,
				TextType='text' if neural else 'ssml',
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
