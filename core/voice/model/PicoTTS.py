import re
import subprocess

from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.TTS import TTS
from core.voice.model.TTSEnum import TTSEnum


class PicoTTS(TTS):
	TTS = TTSEnum.PICO

	def __init__(self, user: User = None):
		super().__init__(user)
		self._online = False
		self._privacyMalus = 0
		self._supportedLangAndVoices = {
			'en-US': {
				'male': {
					'en-US': {
						'neural': False
					}
				}
			},
			'en-GB': {
				'male': {
					'en-GB': {
						'neural': False
					},
				}
			},
			'de-DE': {
				'male': {
					'de-DE': {
						'neural': False
					},
				}
			},
			'es-ES': {
				'male': {
					'es-ES': {
						'neural': False
					},
				}
			},
			'fr-fr': {
				'male': {
					'fr-fr': {
						'neural': False
					},
				}
			},
			'it-it': {
				'male': {
					'it-it': {
						'neural': False
					},
				}
			}
		}


	@staticmethod
	def _checkText(session: DialogSession) -> str:
		text = session.payload['text']
		return re.sub('<.*?>', '', text)


	def onSay(self, session: DialogSession):
		super().onSay(session)

		if not self._text:
			return

		if not self._cacheFile.is_file:
			subprocess.run(['pico2wave', '-l', self._lang, '-w', self._cacheFile, self._text])

		self._speak(file=self._cacheFile, session=session)
