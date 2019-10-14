from pathlib import Path
from typing import Dict, Callable

from core.base.SuperManager import SuperManager
from core.dialog.model.DialogMapping import DialogMapping


class Intent(str):

	def __new__(cls, value: str, *args, **kwargs):
		value = 'hermes/intent/{owner}:' + value
		return super().__new__(cls, value)


	# noinspection PyUnusedLocal
	def __init__(self, value: str, isProtected: bool = False):
		self._owner = SuperManager.getInstance().configManager.getAliceConfigByName('intentsOwner')
		self._protected = isProtected
		self._dialogMapping = None

		if isProtected:
			SuperManager.getInstance().protectedIntentManager.protectIntent(self.decoratedSelf())

		super().__init__()


	def __str__(self) -> str:
		return self.decoratedSelf()


	def __repr__(self) -> str:
		return self.decoratedSelf()


	def __eq__(self, other) -> bool:
		return self.decoratedSelf() == other


	def __hash__(self) -> int:
		return hash(self.decoratedSelf())


	def decoratedSelf(self) -> str:
		return self.format(owner=self._owner)


	def hasDialogMapping(self) -> bool:
		return self.dialogMapping is not None


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


	@property
	def dialogMapping(self) -> DialogMapping:
		return self._dialogMapping


	@dialogMapping.setter
	def dialogMapping(self, value: Dict[str, Dict[int, Callable]]):
		self._dialogMapping = DialogMapping(value)