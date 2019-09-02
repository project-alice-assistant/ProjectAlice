import logging
import subprocess
import uuid
from pathlib import Path

import hashlib
from pydub import AudioSegment

import core.base.Managers as managers
from core.commons import commons
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.TTSEnum import TTSEnum


class TTS:
	TEMP_ROOT = Path('/tmp/tempTTS')
	TTS = None

	def __init__(self, user: User = None):
		self._logger = logging.getLogger('ProjectAlice')
		self._online = False
		self._privacyMalus = 0
		self._supportedLangAndVoices = dict()
		self._client = None
		self._cacheRoot = self.TTS

		if user:
			self._lang = user.lang
			self._type = user.ttsType
			self._voice = user.ttsVoice
		else:
			self._lang = managers.LanguageManager.activeLanguageAndCountryCode
			self._type = managers.ConfigManager.getAliceConfigByName('ttsType')
			self._voice = managers.ConfigManager.getAliceConfigByName('ttsVoice')

		self._cacheFile: Path = Path()
		self._text = ''


	def onStart(self):
		if self._lang not in self._supportedLangAndVoices:
			self._logger.info('[TTS] Lang "{}" not found, falling back to "{}"'.format(self._lang, 'en-US'))
			self._lang = 'en-US'

		if self._type not in self._supportedLangAndVoices[self._lang]:
			self._logger.info('[TTS] Type "{}" not found, falling back to "{}"'.format(self._type, 'male'))
			self._type = 'male'

		if self._voice not in self._supportedLangAndVoices[self._lang][self._type]:
			voice = self._voice
			self._voice = next(iter(self._supportedLangAndVoices[self._lang][self._type]))
			self._logger.info('[TTS] Voice "{}" not found, falling back to "{}"'.format(voice, self._voice))

		self.TEMP_ROOT.mkdir(parents=True, exist_ok=True)

		if self.TTS == TTSEnum.SNIPS:
			voiceFile = 'cmu_{}_{}'.format(managers.LanguageManager.activeCountryCode.lower(), self._voice)
			if not Path(commons.rootDir(), 'system/voices', voiceFile).is_file():
				self._logger.info('[TTS] Using "{}" as TTS with voice "{}" but voice file not found. Downloading...'.format(self.TTS.value, self._voice))

				process = subprocess.run([
					'wget', 'https://github.com/MycroftAI/mimic1/blob/development/voices/{}.flitevox?raw=true'.format(voiceFile),
					'-O', Path(commons.rootDir(),'var/voices/{}.flitevox'.format(voiceFile))
				],
				stdout=subprocess.PIPE)

				if process.returncode > 0:
					self._logger.error('[TTS] Failed downloading voice file, falling back to slt')
					self._voice = next(iter(self._supportedLangAndVoices[self._lang][self._type]))


	def cacheDirectory(self) -> Path:
		return Path(managers.TTSManager.CACHE_ROOT, self.TTS.value, self._lang, self._type, self._voice)

	@property
	def lang(self) -> str:
		return self._lang


	@lang.setter
	def lang(self, value: str):
		self._lang = value if value in self._supportedLangAndVoices else 'en-US'


	@property
	def voice(self) -> str:
		return self._voice


	@voice.setter
	def voice(self, value: str):
		self._voice = value if value.lower() in self._supportedLangAndVoices[self._lang][self._type] else next(iter(self._supportedLangAndVoices[self._lang][self._type]))
			

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
	def _mp3ToWave(src: Path, dest: Path):
		subprocess.run(['mpg123', '-q', '-w', str(dest), str(src)])


	def _hash(self, text: str) -> str:
		string = '{}_{}_{}_{}_{}_22050'.format(text, self.TTS, self._lang, self._type, self._voice)
		return hashlib.md5(string.encode('utf-8')).hexdigest()


	def _speak(self, file: Path, session: DialogSession):
		uid = str(uuid.uuid4())
		managers.MqttServer.playSound(
			soundFile=file.stem,
			sessionId=session.sessionId,
			siteId=session.siteId,
			root=file.parent,
			uid=uid
		)

		duration = round(len(AudioSegment.from_file(file)) / 1000, 2)
		managers.ThreadManager.doLater(interval=duration + 0.1, func=self._sayFinished, args=[session.sessionId, session])


	@staticmethod
	def _sayFinished(sid: str, session: DialogSession):
		if 'id' not in session.payload:
			return

		managers.MqttServer.publish(
			topic='hermes/tts/sayFinished',
			payload={
				'id': session.payload['id'],
				'sessionId': sid
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
