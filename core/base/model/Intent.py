from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Union

import core.base.SuperManager as SM
from core.user.model.AccessLevels import AccessLevel


@dataclass
class Intent:
	topic: str = field(init=False)
	action: str = field(repr=False)
	isProtected: bool = False
	userIntent: bool = True
	authLevel: AccessLevel = AccessLevel.ZERO
	fallbackFunction: Optional[Callable] = None
	_dialogMapping: dict = field(default_factory=dict)


	def __post_init__(self):
		self.topic = f'hermes/intent/{self.action}' if self.userIntent else self.action
		if self.isProtected:
			SM.SuperManager.getInstance().protectedIntentManager.protectIntent(self.topic)


	def __str__(self) -> str:
		return self.topic


	def __repr__(self) -> str:
		return self.topic


	def __hash__(self) -> int:
		return hash(self.topic)


	def __eq__(self, other: str) -> bool:
		return self.topic == other


	def __ne__(self, other) -> bool:
		return self.topic != other


	@property
	def dialogMapping(self) -> dict:
		return self._dialogMapping


	@dialogMapping.setter
	def dialogMapping(self, value: Union[Dict[str, Callable], property]):
		skillName = SM.SuperManager.getInstance().commonsManager.getFunctionCaller(depth=2)
		if isinstance(value, property):
			self._dialogMapping = dict()
		else:
			self._dialogMapping = {
				f'{skillName}:{dialogState}': func for dialogState, func in value.items()
			}


	@property
	def justTopic(self) -> str:
		return self.action


	def addDialogMapping(self, value: Dict[str, Callable], skillName: str):
		for dialogState, func in value.items():
			self.dialogMapping[f'{skillName}:{dialogState}'] = func


	def getMapping(self, session) -> Optional[Callable]:
		return self.dialogMapping.get(session.currentState, self.fallbackFunction)
