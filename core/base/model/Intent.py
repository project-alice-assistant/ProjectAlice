from pathlib import Path
from typing import Dict, Callable, Optional

from core.base.model.ProjectAliceObject import ProjectAliceObject

class Intent(ProjectAliceObject):

	def __init__(self, _value: str, isProtected: bool = False, userIntent: bool = True, authOnly=0):
		self._owner = self.ConfigManager.getAliceConfigByName('intentsOwner')
		self._topic = f'hermes/intent/{self._owner}:{_value}' if userIntent else _value
		self._protected = isProtected
		self._authOnly = int(authOnly)
		self._dialogMapping = dict()
		self._fallbackFunction = None

		if isProtected:
			self.ProtectedIntentManager.protectIntent(self._topic)

		super().__init__()


	def __str__(self) -> str:
		return self._topic


	def __repr__(self) -> str:
		return self._topic


	def __eq__(self, other) -> bool:
		return self._topic == other


	def __hash__(self) -> int:
		return hash(self._topic)


	def decoratedSelf(self) -> str:
		return self._topic.format(owner=self._owner)


	def hasDialogMapping(self) -> bool:
		return bool(self.dialogMapping)


	@property
	def protected(self) -> bool:
		return self._protected


	@property
	def owner(self) -> str:
		return self._owner


	@property
	def justTopic(self) -> str:
		return Path(self._topic).name


	@property
	def justAction(self) -> str:
		return self.justTopic.split(':')[-1]


	@property
	def dialogMapping(self) -> dict:
		return self._dialogMapping


	@dialogMapping.setter
	def dialogMapping(self, value: Dict[str, Callable]):
		skillName = self.Commons.getFunctionCaller(depth=2)
		self._dialogMapping = {
			f'{skillName}:{dialogState}': func for dialogState, func in value.items()
		}


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


	def addDialogMapping(self, value: Dict[str, Callable], skillName: str):
		for dialogState, func in value.items():
			self._dialogMapping[f'{skillName}:{dialogState}'] = func


	def getMapping(self, session) -> Optional[Callable]:
		return self._dialogMapping.get(session.currentState, self._fallbackFunction)
