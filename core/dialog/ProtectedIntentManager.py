import os

from core.base.model.Manager import Manager


class ProtectedIntentManager(Manager):

	NAME = 'ProtectedIntentManager'

	def __init__(self):
		super().__init__(self.NAME)

		# Protected intents cannot be randomly rejected by Alice
		self._protectedIntents = list()


	def protectIntent(self, intent: str):
		intent = self._cleanIntentString(intent)
		if intent not in self._protectedIntents:
			self._protectedIntents.append(intent)


	def isProtectedIntent(self, intent: str) -> bool:
		return self._cleanIntentString(intent) in self._protectedIntents


	@staticmethod
	def _cleanIntentString(intent: str) -> str:
		return os.path.split(intent)[-1] if '/' in intent else intent


	@property
	def protectedIntents(self) -> list:
		return self._protectedIntents
