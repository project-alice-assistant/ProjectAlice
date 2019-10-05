from threading import Event

from core.base.SuperManager import SuperManager
from core.commons import constants, commons


class AliceEvent(Event):

	def __init__(self, name: str):
		super().__init__()
		self._name = name
		self._args = list()


	def set(self, *args, **kwargs) -> None:
		super().set()
		self.broadcast(state='set')


	def clear(self, *args, **kwargs) -> None:
		super().clear()
		self.broadcast(state='clear', *args, **kwargs)


	def broadcast(self, state: str, *args, **kwargs):
		SuperManager.getInstance().broadcast(
			method=f'{self.eventName()}{state.title()}',
			exceptions=[constants.DUMMY],
			args=self._args,
			propagateToModules=True,
			silent=True,
			*args,
			**kwargs
		)


	@property
	def name(self) -> str:
		return self._name


	def eventName(self) -> str:
		return f'on{commons.toCamelCase(self.name)}'