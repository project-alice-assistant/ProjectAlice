from importlib import import_module, reload
from pathlib import Path

from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.TTSEnum import TTSEnum
from core.voice.model.Tts import Tts


class TTSManager(Manager):

	def __init__(self):
		super().__init__()

		self._fallback = None
		self._tts = None
		self._cacheRoot = Path(self.Commons.rootDir(), 'var/cache')


	def onStart(self):
		super().onStart()
		self._loadTTS(self.ConfigManager.getAliceConfigByName('tts').lower())


	def _loadTTS(self, userTTS: str = None, user: User = None, forceTts = None):
		self._fallback = None
		if forceTts:
			systemTTS = forceTts
		else:
			if not userTTS:
				systemTTS = self.ConfigManager.getAliceConfigByName('tts').lower()
			else:
				systemTTS = userTTS.lower()

		keepTTSOffline = self.ConfigManager.getAliceConfigByName('keepTTSOffline')
		stayOffline = self.ConfigManager.getAliceConfigByName('stayCompletlyOffline')
		online = self.InternetManager.online

		self._tts = None

		if systemTTS == TTSEnum.PICO.value:
			package = 'core.voice.model.PicoTts'
		elif systemTTS == TTSEnum.MYCROFT.value:
			package = 'core.voice.model.MycroftTts'
		elif systemTTS == TTSEnum.AMAZON.value:
			package = 'core.voice.model.AmazonTts'
		elif systemTTS == TTSEnum.WATSON.value:
			package = 'core.voice.model.WatsonTts'
		elif systemTTS == TTSEnum.GOOGLE.value:
			package = 'core.voice.model.GoogleTts'
		else:
			package = 'core.voice.model.SnipsTts'

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
			self.logWarning("Couldn't install Tts, falling back to PicoTts")
			from core.voice.model.PicoTts import PicoTts
			self._tts = PicoTts(user)

		if self._tts.online and (not online or keepTTSOffline or stayOffline):
			self._tts = None

		if self._tts is None:
			if not forceTts:
				fallback = self.ConfigManager.getAliceConfigByName('ttsFallback')
				self.logWarning(f'Tts did not satisfy the user settings, falling back to **{fallback}**')
				self._loadTTS(userTTS=userTTS, user=user, forceTts=fallback)
				return
			else:
				self.logFatal('Fallback Tts failed, going down')
				return

		try:
			self._tts.onStart()
		except Exception as e:
			self.logFatal(f"Tts failed starting: {e}")


	@property
	def tts(self) -> Tts:
		return self._tts


	@property
	def cacheRoot(self) -> Path:
		return self._cacheRoot


	def onInternetConnected(self):
		if self.ConfigManager.getAliceConfigByName('stayCompletlyOffline') or self.ConfigManager.getAliceConfigByName('keepTTSOffline'):
			return

		if not self._tts.online:
			self.logInfo('Connected to internet, switching TTS')
			self._loadTTS(self.ConfigManager.getAliceConfigByName('tts').lower())


	def onInternetLost(self):
		if self._tts.online:
			self.logInfo('Internet lost, switching to offline TTS')
			self._loadTTS(self.ConfigManager.getAliceConfigByName('ttsFallback').lower())


	def onSay(self, session: DialogSession):
		if session and session.user != constants.UNKNOWN_USER:
			user: User = self.UserManager.getUser(session.user)
			if user and user.tts:
				self._loadTTS(user.tts, user)

		self._tts.onSay(session)
