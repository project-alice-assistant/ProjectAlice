from pathlib import Path
from typing import Dict, Callable, Optional

from core.base.model.ProjectAliceObject import ProjectAliceObject

class Intent(str, ProjectAliceObject):

	def __new__(cls, value: str, *args, **kwargs):
		if kwargs.get('userIntent', True):
			value = 'hermes/intent/{owner}:' + value
		return super().__new__(cls, value)


	def __init__(self, _value: str, isProtected: bool = False, userIntent: bool = True, authOnly = 0):
		self._owner = self.ConfigManager.getAliceConfigByName('intentsOwner')
		self._protected = isProtected
		self._userIntent = userIntent
		self._authOnly = int(authOnly)
		self._dialogMapping = dict()
		self._fallbackFunction = None

		if isProtected:
			self.ProtectedIntentManager.protectIntent(self.decoratedSelf())

		super().__init__(logDepth=5)


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
		return bool(self.dialogMapping)


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
		return self.justTopic.split(':')[1] if self._userIntent else self.justTopic


	@property
	def dialogMapping(self) -> dict:
		return self._dialogMapping


	@dialogMapping.setter
	def dialogMapping(self, value: Dict[str, Callable]):
		caller = self.Commons.getFunctionCaller()
		self._dialogMapping = {f'{caller}:{state}': func for state, func in value.items()}


	@property
	def fallbackFunction(self) -> Callable:
		return self._fallbackFunction


	@fallbackFunction.setter
	def fallbackFunction(self, value: Callable):
		self._fallbackFunction = value


	@property
	def authOnly(self):
		return self._authOnly


	@authOnly.setter
	def authOnly(self, value):
		self._authOnly = int(value)


	def addDialogMapping(self, value: Dict[str, Callable]):
		caller = self.Commons.getFunctionCaller()
		self._dialogMapping.update({f'{caller}:{state}': func for state, func in value.items()})


	def getMapping(self, session) -> Optional[Callable]:
		return self._dialogMapping.get(session.currentState, self._fallbackFunction)
