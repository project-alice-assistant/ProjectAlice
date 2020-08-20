import getpass
import uuid
from pathlib import Path
from typing import Optional

import hashlib
import tempfile
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User


class Tts(ProjectAliceObject):
	TEMP_ROOT = Path(tempfile.gettempdir(), '/tempTTS')
	TTS = None


	def __init__(self, user: User = None, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self._online = False
		self._privacyMalus = 0
		self._supportedLangAndVoices = dict()
		self._client = None
		self._cacheRoot = self.TTS
		self._user = user

		self._lang = ''
		self._type = ''
		self._voice = ''

		self._cacheFile: Path = Path()
		self._text = ''
		self._speaking = False


	def onStart(self):
		if self._user and self._user.ttsLanguage:
			self._lang = self._user.ttsLanguage
			self.logInfo(f'Language from user settings: **{self._lang}**')
		elif self.ConfigManager.getAliceConfigByName('ttsLanguage'):
			self._lang = self.ConfigManager.getAliceConfigByName('ttsLanguage')
			self.logInfo(f'Language from config: **{self._lang}**')
		else:
			self._lang = self.LanguageManager.activeLanguageAndCountryCode
			self.logInfo(f'Language from active language: **{self._lang}**')

		if self._user and self._user.ttsType:
			self._type = self._user.ttsType
			self.logInfo(f'Type from user settings: **{self._type}**')
		else:
			self._type = self.ConfigManager.getAliceConfigByName('ttsType')
			self.logInfo(f'Type from config: **{self._type}**')

		if self._user and self._user.ttsVoice:
			self._voice = self._user.ttsVoice
			self.logInfo(f'Voice from user settings: **{self._voice}**')
		else:
			self._voice = self.ConfigManager.getAliceConfigByName('ttsVoice')
			self.logInfo(f'Voice from config: **{self._voice}**')

		if self._lang not in self._supportedLangAndVoices:
			self.logWarning(f'Language **{self._lang}** not found, falling back to **en-US**')
			self._lang = 'en-US'

		if self._type not in self._supportedLangAndVoices[self._lang]:
			ttsType = self._type
			self._type = next(iter(self._supportedLangAndVoices[self._lang]))
			self.logWarning(f'Type **{ttsType}** not found for the language, falling back to **{self._type}**')

		if self._voice not in self._supportedLangAndVoices[self._lang][self._type]:
			voice = self._voice
			self._voice = next(iter(self._supportedLangAndVoices[self._lang][self._type]))
			self.logWarning(f'Voice **{voice}** not found for the language and type, falling back to **{self._voice}**')

		if not self.TEMP_ROOT.is_dir():
			self.Commons.runRootSystemCommand(['mkdir', str(self.TEMP_ROOT)])
			self.Commons.runRootSystemCommand(['chown', getpass.getuser(), str(self.TEMP_ROOT)])


	def cacheDirectory(self) -> Path:
		return Path(self.TTSManager.cacheRoot, self.TTS.value, self._lang, self._type, self._voice)


	@property
	def lang(self) -> str:
		return self._lang


	@lang.setter
	def lang(self, value: str):
		self._lang = value if value in self._supportedLangAndVoices else 'en-US'


	@property
	def ttsType(self) -> str:
		return self._type


	@ttsType.setter
	def ttsType(self, value: str):
		self._type = value if value in self._supportedLangAndVoices[self._lang] else next(iter(self._supportedLangAndVoices[self._lang]))


	@property
	def voice(self) -> str:
		return self._voice


	@voice.setter
	def voice(self, value: str):
		self._voice = value if value in self._supportedLangAndVoices[self._lang][self._type] else next(iter(self._supportedLangAndVoices[self._lang][self._type]))


	@property
	def online(self) -> bool:
		return self._online


	@property
	def privacyMalus(self) -> int:
		return self._privacyMalus


	@property
	def supportedLangAndVoices(self) -> dict:
		return self._supportedLangAndVoices


	@staticmethod
	def getWhisperMarkup() -> Optional[tuple]:
		return None


	def _mp3ToWave(self, src: Path, dest: Path):
		self.Commons.runSystemCommand(['mpg123', '-q', '-w', str(dest), str(src)])


	def _hash(self, text: str) -> str:
		string = f'{text}_{self.TTS}_{self._lang}_{self._type}_{self._voice}_{self.AudioServer.SAMPLERATE}'
		return hashlib.md5(string.encode('utf-8')).hexdigest()


	def _speak(self, file: Path, session: DialogSession):
		self._speaking = True
		uid = str(uuid.uuid4())
		self.MqttManager.playSound(
			soundFilename=file.stem,
			location=file.parent,
			sessionId=session.sessionId,
			siteId=session.siteId,
			uid=uid
		)

		try:
			duration = round(len(AudioSegment.from_file(file)) / 1000, 2)
		except CouldntDecodeError:
			self.logError('Error decoding TTS file')
		else:
			self.DialogManager.increaseSessionTimeout(session=session, interval=duration + 0.2)
			self.ThreadManager.doLater(interval=duration + 0.1, func=self._sayFinished, args=[session, uid])


	def _sayFinished(self, session: DialogSession, uid: str):
		self._speaking = False
		self.MqttManager.publish(
			topic=constants.TOPIC_TTS_FINISHED,
			payload={
				'id': uid,
				'sessionId': session.sessionId,
				'siteId': session.siteId
			}
		)


	@staticmethod
	def _checkText(session: DialogSession) -> str:
		return session.payload['text']


	def onSay(self, session: DialogSession):
		self._text = self._checkText(session)
		if self._text:
			self._cacheFile = self.cacheDirectory() / (self._hash(text=self._text) + '.wav')
			self.cacheDirectory().mkdir(parents=True, exist_ok=True)
