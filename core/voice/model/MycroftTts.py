#  Copyright (c) 2021
#
#  This file, MycroftTts.py, is part of Project Alice.
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
from pathlib import Path

from core.base.SuperManager import SuperManager
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.TTSEnum import TTSEnum
from core.voice.model.Tts import Tts


class MycroftTts(Tts):
	TTS = TTSEnum.MYCROFT

	DEPENDENCIES = {
		'system': [
			'gcc',
			'make',
			'pkg-config',
			'automake',
			'libtool',
			'libicu-dev',
			'libpcre2-dev',
			'libasound2-dev'
		],
		'pip'   : {}
	}


	def __init__(self, user: User = None):
		super().__init__(user)

		self._online = False
		self._privacyMalus = 0

		self._mimicDirectory = Path(Path(SuperManager.getInstance().Commons.rootDir()).parent, 'mimic/mimic')

		# TODO => classify genders and countries. First is always default
		self._supportedLangAndVoices = {
			'en-US': {
				'male': {
					'slt': {
						'neural': False
					},
					'aew': {
						'neural': False
					},
					'ahw': {
						'neural': False
					},
					'aup': {
						'neural': False
					},
					'awb': {
						'neural': False
					},
					'axb': {
						'neural': False
					},
					'bdl': {
						'neural': False
					},
					'clb': {
						'neural': False
					},
					'eey': {
						'neural': False
					},
					'fem': {
						'neural': False
					},
					'gka': {
						'neural': False
					},
					'jmk': {
						'neural': False
					},
					'ksp': {
						'neural': False
					},
					'ljm': {
						'neural': False
					},
					'rms': {
						'neural': False
					},
					'rxr': {
						'neural': False
					}
				}
			}
		}


	def checkDependencies(self) -> bool:
		return Path(Path(self.Commons.rootDir()).parent, 'mimic/voices').exists()


	def installDependencies(self) -> bool:
		if not super().installDependencies():
			return False

		try:
			self.Commons.runRootSystemCommand(['sudo', Path(self.Commons.rootDir(), 'system/scripts/installMycroftMimic.sh')])
		except:
			return False
		else:
			return True


	def onSay(self, session: DialogSession):
		super().onSay(session)

		if not self._text:
			return

		if not self._cacheFile.exists():
			if not Path(self._mimicDirectory, 'voices', self._voice + '.flitevox').exists():
				htsvoice = Path(self._mimicDirectory, 'voices', self._voice + '.htsvoice')
				if htsvoice.exists():
					SuperManager.getInstance().CommonsManager.runRootSystemCommand([
						'-u', getpass.getuser(),
						self._mimicDirectory,
						'-t', self._text,
						'-o', self._cacheFile,
						'-voice', htsvoice
					])
				else:
					SuperManager.getInstance().CommonsManager.runRootSystemCommand([
						'-u', getpass.getuser(),
						self._mimicDirectory,
						'-t', self._text,
						'-o', self._cacheFile,
						'-voice', 'slt'
					])
			else:
				SuperManager.getInstance().CommonsManager.runRootSystemCommand([
					'-u', getpass.getuser(),
					self._mimicDirectory,
					'-t', self._text,
					'-o', self._cacheFile,
					'-voice', self._voice
				])
			self.logDebug(f'Generated speech file **{self._cacheFile.stem}**')
		else:
			self.logDebug(f'Using existing cached file **{self._cacheFile.stem}**')

		self._speak(file=self._cacheFile, session=session)
