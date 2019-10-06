from threading import Event

from core.base.SuperManager import SuperManager
from core.commons import constants, commons


class AliceEvent(Event):

	def __init__(self, name: str, onSet: str = None, onClear: str = None):
		super().__init__()
		self._name = name
		self._onSet = onSet
		self._onClear = onClear


	def set(self, **kwargs) -> None:
		super().set()
		if not self._onSet:
			self.broadcast(state='set', **kwargs)
		else:
			SuperManager.getInstance().broadcast(
				method=self._onSet,
				exceptions=[constants.DUMMY],
				propagateToModules=True,
				silent=False,
				**kwargs
			)


	def clear(self, **kwargs) -> None:
		super().clear()

		if not self._onClear:
			self.broadcast(state='clear', **kwargs)
		else:
			SuperManager.getInstance().broadcast(
				method=self._onClear,
				exceptions=[constants.DUMMY],
				propagateToModules=True,
				silent=False,
				**kwargs
			)


	def broadcast(self, state: str, **kwargs):
		SuperManager.getInstance().broadcast(
			method=commons.toCamelCase(f'{self.eventName()} {state}'),
			exceptions=[constants.DUMMY],
			propagateToModules=True,
			silent=True,
			**kwargs
		)


	@property
	def name(self) -> str:
		return self._name


	def eventName(self) -> str:
		return f'on{commons.toCamelCase(self.name)}'