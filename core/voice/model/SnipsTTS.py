# -*- coding: utf-8 -*-
import subprocess

import os

import core.base.Managers as managers
from core.commons import commons
from core.dialog.model.DialogSession import DialogSession
from core.user.model.User import User
from core.voice.model.TTS import TTS
from core.voice.model.TTSEnum import TTSEnum


class SnipsTTS(TTS):
	TTS = TTSEnum.SNIPS

	def __init__(self, user: User = None):
		super().__init__(user)

		self._online = False
		self._privacyMalus = 0

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
		return session.payload['text']


	def onSay(self, session: DialogSession):
		super().onSay(session)

		if not self._cacheFile or not self._text:
			return

		if not os.path.isfile(self._cacheFile):
			subprocess.run([
				'snips-makers-tts',
				'--output',
				self._cacheFile,
				'file://{}/var/voices/cmu_{}_{}.flitevox'.format(
					commons.rootDir(),
					managers.LanguageManager.activeCountryCode.lower(),
					self._voice
				),
				self._text])

		self._speak(file=self._cacheFile, session=session)
