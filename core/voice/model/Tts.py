#  Copyright (c) 2021
#
#  This file, Tts.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:48 CEST

import getpass
import hashlib
import re
import tempfile
from pathlib import Path
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
from re import Match
from typing import Optional

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User


class Tts(ProjectAliceObject):
	TEMP_ROOT = Path(tempfile.gettempdir(), '/tempTTS')
	TTS = None
	SPELL_OUT = re.compile(r'<say-as interpret-as=\"(?:spell-out|characters|verbatim)\">(.+)</say-as>')


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
		self._neuralVoice = False

		self._cacheFile: Path = Path()
		self._text = ''
		self._speaking = False

		self._supportsSSML = False


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
			self._neuralVoice = self._supportedLangAndVoices[self._lang][self._type][self._voice]['neural']
			self.logWarning(f'Voice **{voice}** not found for the language and type, falling back to **{self._voice}**')
		else:
			self._neuralVoice = self._supportedLangAndVoices[self._lang][self._type][self._voice]['neural']

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


	@property
	def speaking(self) -> bool:
		return self._speaking


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
		session.lastWasSoundPlayOnly = False

		self.MqttManager.playSound(
			soundFilename=file.stem,
			location=file.parent,
			sessionId=session.sessionId,
			deviceUid=session.deviceUid
		)

		try:
			duration = round(len(AudioSegment.from_file(file)) / 1000, 2)
		except CouldntDecodeError:
			self.logError('Error decoding TTS file')
			file.unlink()
			self.onSay(session)
		else:
			self.DialogManager.increaseSessionTimeout(session=session, interval=duration + 1)

			if session.deviceUid == self.DeviceManager.getMainDevice().uid:
				self.ThreadManager.doLater(interval=duration + 0.2, func=self._sayFinished, args=[session])


	def _sayFinished(self, session: DialogSession):
		self._speaking = False
		self.MqttManager.publish(
			topic=constants.TOPIC_TTS_FINISHED,
			payload={
				'id'       : session.sessionId,
				'sessionId': session.sessionId,
				'deviceUid': session.deviceUid
			}
		)


	def onSayFinished(self, session: DialogSession, uid: str = None):
		self._speaking = False


	def _checkText(self, session: DialogSession) -> str:
		text = session.payload['text']
		if not self._supportsSSML:
			# We need to remove all ssml tags but transform some first
			text = re.sub(self.SPELL_OUT, self._replaceSpellOuts, text)
			return ' '.join(re.sub('<.*?>', ' ', text).split())
		else:
			if not '<speak>' in text:
				text = f'<speak>{text}</speak>'
			return text


	@staticmethod
	def _replaceSpellOuts(matching: Match) -> str:
		return '<break time="160ms"/>'.join(matching.group(1))


	def onSay(self, session: DialogSession) -> None:
		"""
		cleans the requested text for speaking if required and prepares the cache
		Tts provides must redefine this method, but should call it at the start of their redefinition.
		:param session:
		:return:
		"""
		self._text = self._checkText(session)
		if self._text:
			self._cacheFile = self.cacheDirectory() / (self._hash(text=self._text) + '.wav')
			self.cacheDirectory().mkdir(parents=True, exist_ok=True)
