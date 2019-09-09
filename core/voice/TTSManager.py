from pathlib import Path

from core.base.SuperManager import SuperManager
from core.base.model.Manager import Manager
from core.commons import commons, constants
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.PicoTTS import PicoTTS
from core.voice.model.TTS import TTS
from core.voice.model.TTSEnum import TTSEnum


class TTSManager(Manager):
	NAME = 'TTSManager'

	CACHE_ROOT = Path(commons.rootDir(), 'var/cache')

	def __init__(self):
		super().__init__(self.NAME)

		self._fallback = None
		self._tts = None


	def _loadTTS(self, tts: str, user: User = None) -> TTSEnum:
		try:
			tts = TTSEnum(tts)
		except:
			tts = TTSEnum.SNIPS

		if tts == TTSEnum.SNIPS:
			from core.voice.model.SnipsTTS import SnipsTTS
			self._tts = SnipsTTS(user)
		elif tts == TTSEnum.PICO:
			self._tts = PicoTTS(user)
		elif tts == TTSEnum.MYCROFT:
			if not Path(Path(commons.rootDir()).parent, 'mimic/voices').is_dir():
				self._logger.warning('[{}] Trying to use Mycroft as TTS but files not available, falling back to picotts'.format(self.NAME))
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


	def onInternetLost(self, *args):
		if self._tts.online:
			self._fallback = PicoTTS()


	def onInternetConnected(self, *args):
		self._fallback = None


	def onStart(self):
		super().onStart()

		if (SuperManager.getInstance().configManager.getAliceConfigByName('stayCompletlyOffline') or SuperManager.getInstance().configManager.getAliceConfigByName('keepTTSOffline')) and self._tts.online:
			self._tts = PicoTTS()
		else:
			tts = self._loadTTS(SuperManager.getInstance().configManager.getAliceConfigByName('tts').lower())
			self._logger.info('[{}] Started "{}" TTS'.format(self.name, tts.value))

		self._tts.onStart()


	def onSay(self, session: DialogSession):
		if self._fallback:
			self._fallback.onSay(session)
		else:
			if session.user != constants.UNKNOWN_USER:
				user: User = SuperManager.getInstance().userManager.getUser(session.user)
				if user and user.tts:
					self._loadTTS(user.tts, user)
					self._tts.onStart()

			self._tts.onSay(session)
