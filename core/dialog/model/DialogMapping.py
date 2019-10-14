from typing import Callable, Dict

from core.util.model.Logger import Logger


class DialogMapping(Logger):

	def __init__(self, mapping: Dict[str, Dict[int, Callable]]):
		super().__init__(depth=6)

		self._mapping = mapping
		self._state = 0


	def onDialog(self, intent, session) -> bool:
		if not session.previousIntent:
			return False

		if session.previousIntent in self._mapping:
			try:
				consumed = self._mapping[session.previousIntent][self._state](intent=intent, session=session)
				self._state += 1

				if int(self.state) >= len(self._mapping[session.previousIntent]):
					self._state = 0

				return consumed
			except Exception as e:
				self.logError(f"Can't continue dialog for intent {intent}, method to call for previous intent {session.previousIntent} not found: {e}")

		return False


	@property
	def state(self) -> int:
		return self._state


	@state.setter
	def state(self, value: int):
		self._state = value