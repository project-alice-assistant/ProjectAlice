# -*- coding: utf-8 -*-
import logging
import subprocess
import uuid

import hashlib
import os
from pydub import AudioSegment

import core.base.Managers as managers
from core.commons import commons
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.TTSEnum import TTSEnum


class TTS:
	TEMP_ROOT = os.path.join('/tmp', 'tempTTS')
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

		self._cacheDirectory = ''
		self._cacheFile = ''
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

		self._cacheDir()

		if not os.path.isdir(self.TEMP_ROOT):
			os.mkdir(self.TEMP_ROOT)

		if self.TTS == TTSEnum.SNIPS:
			voiceFile = 'cmu_{}_{}'.format(managers.LanguageManager.activeCountryCode.lower(), self._voice)
			if not os.path.isfile(os.path.join(commons.rootDir(), 'system', 'voices', voiceFile)):
				self._logger.info('[TTS] Using "{}" as TTS with voice "{}" but voice file not found. Downloading...'.format(self.TTS.value, self._voice))

				process = subprocess.run([
					'wget', 'https://github.com/MycroftAI/mimic1/blob/development/voices/{}.flitevox?raw=true'.format(voiceFile),
					'-O', os.path.join(commons.rootDir(), 'var', 'voices', '{}.flitevox'.format(voiceFile))
				],
				stdout=subprocess.PIPE)

				if process.returncode > 0:
					self._logger.error('[TTS] Failed downloading voice file, falling back to slt')
					self._voice = next(iter(self._supportedLangAndVoices[self._lang][self._type]))


	def _cacheDir(self):
		self._cacheDirectory = os.path.join(managers.TTSManager.CACHE_ROOT, self.TTS.value, self._lang, self._type, self._voice)


	@property
	def lang(self) -> str:
		return self._lang


	@lang.setter
	def lang(self, value: str):
		if value not in self._supportedLangAndVoices:
			self._lang = 'en-US'
		else:
			self._lang = value

		self._cacheDir()


	@property
	def voice(self) -> str:
		return self._voice


	@voice.setter
	def voice(self, value: str):
		if value.lower() not in self._supportedLangAndVoices[self._lang][self._type]:
			self._voice = next(iter(self._supportedLangAndVoices[self._lang][self._type]))
		else:
			self._voice = value

		self._cacheDir()


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
	def _mp3ToWave(src: str, dest: str):
		subprocess.run(['mpg123', '-q', '-w', dest, src])


	def _hash(self, text: str) -> str:
		string = '{}_{}_{}_{}_{}_22050'.format(text, self.TTS, self._lang, self._type, self._voice)
		return hashlib.md5(string.encode('utf-8')).hexdigest()


	def _speak(self, file: str, session: DialogSession):
		uid = str(uuid.uuid4())
		managers.MqttServer.playSound(
			soundFile=os.path.splitext(os.path.basename(file))[0],
			sessionId=session.sessionId,
			siteId=session.siteId,
			root=os.path.dirname(file),
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
		if not self._text:
			self._cacheFile = ''
			self._text = ''
			return

		self._cacheFile = os.path.join(self._cacheDirectory, self._hash(text=self._text) + '.wav')

		if not os.path.isdir(os.path.dirname(self._cacheFile)):
			os.makedirs(os.path.dirname(self._cacheFile), exist_ok=True)
