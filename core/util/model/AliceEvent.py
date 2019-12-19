from threading import Event

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants


class AliceEvent(Event, ProjectAliceObject):

	def __init__(self, name: str, onSet: str = None, onClear: str = None):
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
			self.broadcast(
				method=self._onSet,
				exceptions=[constants.DUMMY],
				propagateToSkills=True,
				**kwargs
			)


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
			self.broadcast(
				method=self._onClear,
				exceptions=[constants.DUMMY],
				propagateToSkills=True,
				**self._kwargs
			)


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
