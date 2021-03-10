from dataclasses import dataclass, field
from typing import Callable

from core.base.model.StateType import StateType
from core.util.model.Logger import Logger


@dataclass
class State:

	name: str
	currentState: StateType = StateType.BORN
	logger: Logger = Logger(prepend='[State]')
	callbacks: list = field(default_factory=list)


	def subscribe(self, callback: Callable):
		self.callbacks.append(callback)


	def unsubscribe(self, callback: Callable):
		self.callbacks.remove(callback)


	def setState(self, newState: StateType):
		oldState = self.currentState
		self.currentState = newState
		for callback in self.callbacks:
			try:
				callback(oldState, newState)
			except:
				self.logger.logWarning(f'Failed callback for state {self.name}')


	def __repr__(self) -> str:
		return f'State "{self.name}" Current state "{self.currentState.value}"'

