from pathlib import Path

from core.base.SuperManager import SuperManager


class Intent(str):

	def __new__(cls, value: str, *args: tuple, **kwargs: dict):
		value = 'hermes/intent/{owner}:' + value
		return super().__new__(cls, value)


	# noinspection PyUnusedLocal
	def __init__(self, value: str, isProtected: bool = False):
		self._owner = SuperManager.getInstance().configManager.getAliceConfigByName('intentsOwner')
		self._protected = isProtected

		if isProtected:
			SuperManager.getInstance().protectedIntentManager.protectIntent(self.decoratedSelf())

		super().__init__()


	def __str__(self):
		return self.decoratedSelf()


	def __repr__(self):
		return self.decoratedSelf()


	def __eq__(self, other):
		return self.decoratedSelf() == other


	def __hash__(self):
		return hash(self.decoratedSelf())


	def decoratedSelf(self) -> str:
		return self.format(owner=self._owner)


	@property
	def protected(self) -> bool:
		return self._protected


	@property
	def owner(self) -> str:
		return self._owner


	@owner.setter
	def owner(self, value: str):
		self._owner = value


	@property
	def justTopic(self) -> str:
		return Path(self.decoratedSelf()).name


	@property
	def justAction(self) -> str:
		return self.justTopic.split(':')[1]
