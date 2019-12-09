from typing import Callable, Dict

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants


class DialogMapping(ProjectAliceObject):

	def __init__(self, mapping: Dict[str, Callable]):
		super().__init__(depth=6)

		caller = self.Commons.getFunctionCaller()
		self._mapping = {f'{caller}:{state}': func for state, func in mapping.items()}
		self._state = constants.DEFAULT


	def onDialog(self, session, caller: str) -> bool:
		state = f'{caller}:{session.currentState}'

		if state in self._mapping:
			try:
				return self._mapping[state](session=session)
			except Exception as e:
				self.logError(f"Can't continue dialog for intent {session.intentName}, method to call for previous intent {session.previousIntent} not found: {e}")

		return False


	def addMappings(self, mapping: Dict[str, Callable]):
		caller = self.Commons.getFunctionCaller()
		self._mapping.update({f'{caller}:{state}': func for state, func in mapping.items()})

	@property
	def state(self) -> str:
		return self._state


	@state.setter
	def state(self, value: str):
		self._state = value
