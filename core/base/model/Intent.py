# -*- coding: utf-8 -*-
import os
from core.base import Managers


class Intent(str):

	def __new__(cls, value: str, *args, **kwargs):
		value = 'hermes/intent/{owner}:' + value
		return super().__new__(cls, value)


	# noinspection PyUnusedLocal
	def __init__(self, value: str, isProtected: bool = False):
		self._owner = Managers.ConfigManager.getAliceConfigByName('intentsOwner')
		self._protected = isProtected

		if isProtected:
			Managers.ProtectedIntentManager.protectIntent(self.decoratedSelf())

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
		pathPair = os.path.split(self)
		intentNamePair = pathPair[1].split(':')

		return pathPair[0] + '/' + self._owner + ':' + str(intentNamePair[1])


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
		return os.path.split(self.decoratedSelf())[-1]

	@property
	def justAction(self) -> str:
		return os.path.split(self.decoratedSelf())[-1].split(':')[1]
