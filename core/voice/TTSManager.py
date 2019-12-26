from pathlib import Path

from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.PicoTTS import PicoTTS
from core.voice.model.TTS import TTS
from core.voice.model.TTSEnum import TTSEnum


class TTSManager(Manager):
	NAME = 'TTSManager'

	def __init__(self):
		super().__init__(self.NAME)

		self._fallback = None
		self._tts = None
		self._cacheRoot = Path(self.Commons.rootDir(), 'var/cache')


	def onStart(self):
		super().onStart()

		tts = self._loadTTS(self.ConfigManager.getAliceConfigByName('tts').lower())

		if (self.ConfigManager.getAliceConfigByName('stayCompletlyOffline') or self.ConfigManager.getAliceConfigByName('keepTTSOffline')) and self._tts.online:
			self._tts = PicoTTS()
			self.logInfo('Started "Pico" TTS')
		else:
			self.logInfo(f'Started "{tts.value}" TTS')

		self._tts.onStart()


	def _loadTTS(self, tts: str, user: User = None) -> TTSEnum:
		try:
			tts = TTSEnum(tts)
		except:
			tts = TTSEnum.SNIPS

		if tts == TTSEnum.PICO:
			self._tts = PicoTTS(user)
		elif tts == TTSEnum.MYCROFT:
			if not Path(Path(self.Commons.rootDir()).parent, 'mimic/voices').is_dir():
				self.logWarning('Trying to use Mycroft as TTS but files not available, falling back to picotts')
				self._tts = PicoTTS(user)
				tts = TTSEnum.PICO
			else:
				from core.voice.model.MycroftTTS import MycroftTTS
				self._tts = MycroftTTS(user)
		elif tts == TTSEnum.AMAZON:
			from core.voice.model.AmazonTTS import AmazonTTS
			self._tts = AmazonTTS(user)
		elif tts == TTSEnum.GOOGLE:
			from core.voice.model.GoogleTTS import GoogleTTS
			self._tts = GoogleTTS(user)
		else:
			from core.voice.model.SnipsTTS import SnipsTTS
			self._tts = SnipsTTS(user)

		return tts


	@property
	def tts(self) -> TTS:
		return self._tts


	@property
	def cacheRoot(self) -> Path:
		return self._cacheRoot


	def onInternetLost(self):
		if self._tts.online:
			self._fallback = PicoTTS()


	def onInternetConnected(self):
		self._fallback = None


	def onSay(self, session: DialogSession):
		if self._fallback:
			self._fallback.onSay(session)
			return

		if session and session.user != constants.UNKNOWN_USER:
			user: User = self.UserManager.getUser(session.user)
			if user and user.tts:
				self._loadTTS(user.tts, user)
				self._tts.onStart()

		self._tts.onSay(session)
