from threading import Event

from core.base.SuperManager import SuperManager
from core.commons import constants, commons


class AliceEvent(Event):

	def __init__(self, name: str):
		super().__init__()
		self._name = name
		self._args = list()


	def set(self) -> None:
		super().set()
		SuperManager.getInstance().broadcast(
			method=self.eventName(),
			exceptions=[constants.DUMMY],
			args=self._args,
			propagateToModules=True
		)


	def eventName(self) -> str:
		return f'on{commons.toCamelCase(self.name)}'


	def clear(self) -> None:
		super().clear()


	@property
	def name(self) -> str:
		return self._name
