from core.base.model.Manager import Manager


class ProtectedIntentManager(Manager):

	def __init__(self):
		super().__init__()

		# Protected intents cannot be randomly rejected by Alice
		self._protectedIntents = list()


	def protectIntent(self, intentName: str):
		if intentName not in self._protectedIntents:
			self._protectedIntents.append(intentName)


	def isProtectedIntent(self, intentName: str) -> bool:
		return intentName in self._protectedIntents


	@property
	def protectedIntents(self) -> list:
		return self._protectedIntents
