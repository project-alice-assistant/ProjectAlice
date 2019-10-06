from threading import Event

from core.base.SuperManager import SuperManager
from core.commons import constants, commons


class AliceEvent(Event):

	def __init__(self, name: str, onSet: str = None, onClear: str = None):
		super().__init__()
		self._name = name
		self._onSet = onSet
		self._onClear = onClear
		self._args = list()


	def set(self, *args, **kwargs) -> None:
		super().set()
		if not self._onSet:
			self.broadcast(state='set', *args, **kwargs)
		else:
			SuperManager.getInstance().broadcast(
				method=self._onSet,
				exceptions=[constants.DUMMY],
				args=self._args,
				propagateToModules=True,
				silent=False,
				*args,
				**kwargs
			)


	def clear(self, *args, **kwargs) -> None:
		super().clear()

		if not self._onClear:
			self.broadcast(state='clear', *args, **kwargs)
		else:
			SuperManager.getInstance().broadcast(
				method=self._onClear,
				exceptions=[constants.DUMMY],
				args=self._args,
				propagateToModules=True,
				silent=False,
				*args,
				**kwargs
			)


	def broadcast(self, state: str, *args, **kwargs):
		SuperManager.getInstance().broadcast(
			method=f'{self.eventName()}{state.title()}',
			exceptions=[constants.DUMMY],
			args=self._args,
			propagateToModules=True,
			silent=False,
			*args,
			**kwargs
		)


	@property
	def name(self) -> str:
		return self._name


	def eventName(self) -> str:
		return f'on{commons.toCamelCase(self.name)}'