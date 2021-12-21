#  Copyright (c) 2021
#
#  This file, Intent.py, is part of Project Alice.
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
from typing import Callable, Dict, Optional, Union

import core.base.SuperManager as SM
from core.user.model.AccessLevels import AccessLevel


@dataclass
class Intent(object):
	topic: str = field(init=False)
	action: str = field(repr=False)
	userIntent: bool = True
	authLevel: AccessLevel = AccessLevel.ZERO
	fallbackFunction: Optional[Callable] = None
	_dialogMapping: dict = field(default_factory=dict)

	# TODO remove me
	isProtected: bool = False


	def __post_init__(self):
		self.topic = f'hermes/intent/{self.action}' if self.userIntent else self.action
		if self.isProtected:
			print('Usage of `isProtected` is deprecated')


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
			try:
				self._dialogMapping = {
					f'{skillName}:{dialogState}': func for dialogState, func in value.items()
				}
			except:
				self._dialogMapping = dict()


	@property
	def justTopic(self) -> str:
		return self.action


	def addDialogMapping(self, value: Dict[str, Callable], skillName: str):
		for dialogState, func in value.items():
			if callable(func):
				self.dialogMapping[f'{skillName}:{dialogState}'] = func


	def getMapping(self, session) -> Optional[Callable]:
		return self.dialogMapping.get(session.currentState, self.fallbackFunction)
