#  Copyright (c) 2021
#
#  This file, TTSManager.py, is part of Project Alice.
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
#  Last modified: 2021.07.31 at 15:54:28 CEST

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
		self.readyFallbackTTS()


	def _loadTTS(self, userTTS: str = None, user: User = None, forceTts=None):
		self._fallback = None
		if forceTts:
			systemTTS = forceTts
		else:
			if not userTTS:
				systemTTS = self.ConfigManager.getAliceConfigByName('tts').lower()
			else:
				systemTTS = userTTS.lower()

		keepTTSOffline = self.ConfigManager.getAliceConfigByName('keepTTSOffline')
		stayOffline = self.ConfigManager.getAliceConfigByName('stayCompletelyOffline')
		online = self.InternetManager.online

		self._tts = None
		package = self.getTTSPackage(systemTTS)
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
			if not forceTts:
				fallback = self.ConfigManager.getAliceConfigByName('ttsFallback')
				self.logWarning(f'Tts failed starting, falling back to **{fallback}**')
				self._loadTTS(userTTS=userTTS, user=user, forceTts=fallback)
			else:
				self.logFatal(f"Tts failed starting: {e}")


	def readyFallbackTTS(self):
		package = self.getTTSPackage(self.ConfigManager.getAliceConfigByName('ttsFallback'))
		module = import_module(package)
		tts = getattr(module, package.rsplit('.', 1)[-1])
		fallbackTTS = tts()
		if not fallbackTTS.checkDependencies() and not fallbackTTS.installDependencies():
			self.logWarning('Fallback TTS could not be installed')


	@staticmethod
	def getTTSPackage(tts: str) -> str:
		if tts == TTSEnum.PICO.value:
			return 'core.voice.model.PicoTts'
		elif tts == TTSEnum.MYCROFT.value:
			return 'core.voice.model.MycroftTts'
		elif tts == TTSEnum.AMAZON.value:
			return 'core.voice.model.AmazonTts'
		elif tts == TTSEnum.WATSON.value:
			return 'core.voice.model.WatsonTts'
		elif tts == TTSEnum.GOOGLE.value:
			return 'core.voice.model.GoogleTts'
		else:
			return 'core.voice.model.SnipsTts'


	@property
	def tts(self) -> Tts:
		return self._tts


	@property
	def speaking(self) -> bool:
		if not self._tts:
			return False
		return self._tts.speaking


	@property
	def cacheRoot(self) -> Path:
		return self._cacheRoot


	def onInternetConnected(self):
		if self.ConfigManager.getAliceConfigByName('stayCompletelyOffline') or self.ConfigManager.getAliceConfigByName('keepTTSOffline'):
			return

		if not self._tts.online:
			self.logInfo('Connected to internet, switching TTS')
			self._loadTTS(self.ConfigManager.getAliceConfigByName('tts').lower())


	def onInternetLost(self):
		if self._tts.online:
			self.logInfo('Internet lost, switching to offline TTS')
			self._loadTTS(self.ConfigManager.getAliceConfigByName('ttsFallback').lower())


	def onSay(self, session: DialogSession):
		if session.textOnly:
			return

		if 'text' not in session.payload:
			self.logWarning('Was asked to say something but no text provided')
			self.MqttManager.endSession(sessionId=session.sessionId, forceEnd=True)
			return

		if session and session.user != constants.UNKNOWN_USER:
			user: User = self.UserManager.getUser(session.user)
			if user and user.tts:
				self._loadTTS(user.tts, user)

		self._tts.onSay(session)
