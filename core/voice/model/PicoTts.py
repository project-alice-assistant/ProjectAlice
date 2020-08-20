import re

from core.base.SuperManager import SuperManager
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.TTSEnum import TTSEnum
from core.voice.model.Tts import Tts


class PicoTts(Tts):
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
			'fr-FR': {
				'male': {
					'fr-FR': {
						'neural': False
					},
				}
			},
			'it-IT': {
				'male': {
					'it-IT': {
						'neural': False
					},
				}
			}
		}


	@staticmethod
	def _checkText(session: DialogSession) -> str:
		text = session.payload['text']
		return ' '.join(re.sub('<.*?>', ' ', text).split())


	def onSay(self, session: DialogSession):
		super().onSay(session)

		if not self._text:
			return

		if not self._cacheFile.exists():
			result = SuperManager.getInstance().commonsManager.runRootSystemCommand(['pico2wave', '-l', self._lang, '-w', self._cacheFile, f'"{self._text}"'])
			if result.returncode:
				self.logError(f'Something went wrong generating speech file: {result.stderr}')
				return
			else:
				self.logDebug(f'Generated speech file **{self._cacheFile.stem}**')
		else:
			self.logDebug(f'Using existing cached file **{self._cacheFile.stem}**')

		self._speak(file=self._cacheFile, session=session)
