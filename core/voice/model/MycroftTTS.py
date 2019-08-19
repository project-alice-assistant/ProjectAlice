# -*- coding: utf-8 -*-
import getpass
import subprocess

import os
import re

from core.commons import commons
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.TTS import TTS
from core.voice.model.TTSEnum import TTSEnum


class MycroftTTS(TTS):
	TTS = TTSEnum.MYCROFT

	def __init__(self, user: User = None):
		super().__init__(user)

		self._online = False
		self._privacyMalus = 0

		self._mimicDirectory = os.path.join(commons.rootDir(), '..', 'mimic', 'mimic')

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


	@staticmethod
	def _checkText(session: DialogSession) -> str:
		text = session.payload['text']
		return re.sub('<.*?>', '', text)


	def onSay(self, session: DialogSession):
		super().onSay(session)

		if not self._cacheFile or not self._text:
			return

		if not os.path.isfile(self._cacheFile):
			if not os.path.isfile(os.path.join(self._mimicDirectory, 'voices', self._voice + '.flitevox')):
				htsvoice = os.path.join(self._mimicDirectory, 'voices', self._voice + '.htsvoice')
				if os.path.isfile(htsvoice):
					subprocess.run([
						'sudo',
						'-u', getpass.getuser(),
						self._mimicDirectory,
						'-t', self._text,
						'-o', self._cacheFile,
						'-voice', htsvoice
					])
				else:
					subprocess.run([
						'sudo',
						'-u', getpass.getuser(),
						self._mimicDirectory,
						'-t', self._text,
						'-o', self._cacheFile,
						'-voice', 'slt'
					])
			else:
				subprocess.run([
					'sudo',
					'-u', getpass.getuser(),
					self._mimicDirectory,
					'-t', self._text,
					'-o', self._cacheFile,
					'-voice', self._voice
				])

		self._speak(file=self._cacheFile, session=session)
