from typing import Callable, Dict

from core.commons import commons, constants
from core.util.model.Logger import Logger


class DialogMapping(Logger):

	def __init__(self, mapping: Dict[str, Callable]):
		super().__init__(depth=6)

		caller = commons.getFunctionCaller()
		self._mapping = {f'{caller}:{state}': func for state, func in mapping.items()}
		self._state = constants.DEFAULT


	def onDialog(self, intent, session, caller: str) -> bool:
		state = f'{caller}:{session.currentState}'

		if state in self._mapping:
			try:
				return self._mapping[state](session=session, intent=intent)
			except Exception as e:
				self.logError(f"Can't continue dialog for intent {intent}, method to call for previous intent {session.previousIntent} not found: {e}")

		return False


	@property
	def state(self) -> str:
		return self._state


	@state.setter
	def state(self, value: str):
		self._state = value
