from core.base.model.Manager import Manager


class ProtectedIntentManager(Manager):

	def __init__(self):
		super().__init__()

		# Protected intents cannot be randomly rejected by Alice
		self._protectedIntents = set()


	def protectIntent(self, intentName: str):
		self._protectedIntents.add(intentName)


	def isProtectedIntent(self, intentName: str) -> bool:
		return intentName in self._protectedIntents


	@property
	def protectedIntents(self) -> set:
		return self._protectedIntents
