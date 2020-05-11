from importlib import import_module, reload
from pathlib import Path

from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.PicoTTS import PicoTTS
from core.voice.model.TTSEnum import TTSEnum
from core.voice.model.Tts import TTS


class TTSManager(Manager):

	def __init__(self):
		super().__init__()

		self._fallback = None
		self._tts = None
		self._cacheRoot = Path(self.Commons.rootDir(), 'var/cache')


	def onStart(self):
		super().onStart()
		self._loadTTS(self.ConfigManager.getAliceConfigByName('tts').lower())


	def _loadTTS(self, userTTS: str = None, user: User = None):
		if not userTTS:
			systemTTS = self.ConfigManager.getAliceConfigByName('tts').lower()
		else:
			systemTTS = userTTS.lower()

		keepTTSOffline = self.ConfigManager.getAliceConfigByName('keepTTSOffline')
		stayOffline = self.ConfigManager.getAliceConfigByName('stayCompletlyOffline')
		online = self.InternetManager.online

		self._tts = None

		if systemTTS == TTSEnum.PICO.value:
			package = 'core.voice.model.PicoTTS'
		elif systemTTS == TTSEnum.MYCROFT.value:
			package = 'core.voice.model.MycroftTTS'
		elif systemTTS == TTSEnum.AMAZON.value:
			package = 'core.voice.model.AmazonTTS'
		elif systemTTS == TTSEnum.WATSON.value:
			package = 'core.voice.model.WatsonTTS'
		elif systemTTS == TTSEnum.GOOGLE.value:
			package = 'core.voice.model.GoogleTTS'
		else:
			package = 'core.voice.model.SnipsTTS'

		module = import_module(package)
		tts = getattr(module, package.rsplit('.', 1)[-1])
		self._tts = tts(user)

		if not self._tts.checkDependencies():
			if not self._tts.installDependencies():
				self._tts = None
			else:
				module = reload(module)
				tts = getattr(module, package.rsplit('.', 1)[-1])
				self._tts = tts(user)

		if self._tts is None:
			self.logWarning("Couldn't install TTS, falling back to PicoTTS")
			from core.voice.model.PicoTTS import PicoTTS

			self._tts = PicoTTS(user)

		if self._tts.online and (not online or keepTTSOffline or stayOffline):
			self._tts = None

		if self._tts is None:
			self.logWarning('TTS did not satisfy the user settings, falling back to PicoTTS')
			from core.voice.model.PicoTTS import PicoTTS

			self._tts = PicoTTS(user)

		try:
			self._tts.onStart()
		except Exception as e:
			self.logFatal(f"TTS failed starting: {e}")


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

		self._tts.onSay(session)
