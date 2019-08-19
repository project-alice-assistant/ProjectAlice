# -*- coding: utf-8 -*-
import os

import core.base.Managers    as managers
from core.base.Manager import Manager


class ProtectedIntentManager(Manager):

	NAME = 'ProtectedIntentManager'

	def __init__(self, mainClass):
		super().__init__(mainClass, self.NAME)

		managers.ProtectedIntentManager = self

		# Protected intents cannot be randomly rejected by Alice
		self._protectedIntents = list()


	def protectIntent(self, intent: str):
		intent = self._cleanIntentString(intent)
		if intent not in self._protectedIntents:
			self._protectedIntents.append(str(intent))


	def isProtectedIntent(self, intent: str) -> bool:
		intent = self._cleanIntentString(intent)
		return str(intent) in self._protectedIntents


	@staticmethod
	def _cleanIntentString(intent: str) -> str:
		if '/' in intent:
			intent = os.path.split(intent)[-1]

		return intent


	@property
	def protectedIntents(self) -> list:
		return self._protectedIntents