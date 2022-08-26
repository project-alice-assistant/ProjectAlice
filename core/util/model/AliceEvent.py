#  Copyright (c) 2021
#
#  This file, AliceEvent.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:47 CEST

from threading import Event
from typing import Callable, Union

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants


class AliceEvent(Event, ProjectAliceObject):

	def __init__(self, name: str, onSet: Union[str, Callable] = None, onClear: Union[str, Callable] = None):
		super().__init__()
		self._name = name
		self._onSet = onSet
		self._onClear = onClear
		self._kwargs = dict()


	def set(self, **kwargs) -> None:
		super().set()

		if kwargs:
			self._kwargs = kwargs
		else:
			kwargs = dict()

		if not self._onSet:
			self.doBroadcast(state='set', **kwargs)
		else:
			if isinstance(self._onSet, str):
				self.broadcast(
					method=self._onSet,
					exceptions=[constants.DUMMY],
					propagateToSkills=True,
					**kwargs
				)
			else:
				self._onSet()


	def clear(self, **kwargs) -> None:
		"""
		Clears an event and calls the onClear method if any or builds a "onYourEventName" broadcast
		:param kwargs:
		:return:
		"""
		super().clear()

		if kwargs:
			self._kwargs = {**kwargs, **self._kwargs}

		if not self._onClear:
			self.doBroadcast(state='clear', **self._kwargs)
		else:
			if isinstance(self._onClear, str):
				self.broadcast(
					method=self._onClear,
					exceptions=[constants.DUMMY],
					propagateToSkills=True,
					**self._kwargs
				)
			else:
				self._onClear()


	def cancel(self) -> None:
		"""
		Clears an event but doesn't call the onClear event
		:return:
		"""
		super().clear()


	def doBroadcast(self, state: str, **kwargs):
		self.broadcast(
			method=self.eventName(state),
			exceptions=[constants.DUMMY],
			propagateToSkills=True,
			**kwargs
		)


	@property
	def name(self) -> str:
		return self._name


	def eventName(self, state: str) -> str:
		return f'on{self.Commons.toPascalCase(self.name)}{state.capitalize()}'
