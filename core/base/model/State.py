#  Copyright (c) 2021
#
#  This file, State.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:46 CEST

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
