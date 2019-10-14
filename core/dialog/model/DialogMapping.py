import collections
from typing import Callable, Dict

from core.base.model.Intent import Intent
from core.dialog.model.DialogSession import DialogSession
from core.util.model.Logger import Logger


class DialogMapping(Logger):

	def __init__(self, mapping: Dict[str, collections.OrderedDict[int, Callable]]):
		super().__init__(depth=6)

		self._mapping = mapping
		self._state = 0


	def onDialog(self, intent: Intent, session: DialogSession):
		if not session.previousIntent:
			return

		if session.previousIntent in self._mapping:
			try:
				self._mapping[session.previousIntent][self._state](intent=intent, session=session)
				self._state += 1

				if int(self.state) >= len(self._mapping[session.previousIntent]):
					self._state = 0
			except Exception as e:
				self.logError(f"Can't continue dialog for intent {intent}, method to call for previous intent {session.previousIntent} not found: {e}")
		else:
			return


	@property
	def state(self) -> int:
		return self._state


	@state.setter
	def state(self, value: int):
		self._state = i