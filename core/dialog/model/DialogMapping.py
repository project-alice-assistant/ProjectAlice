import collections
from typing import Callable

from core.base.model.Intent import Intent
from core.dialog.model.DialogSession import DialogSession
from core.util.model.Logger import Logger


class DialogMapping(Logger):

	def __init__(self, defaultFunction: Callable, mapping: collections.OrderedDict[str, Callable]):
		super().__init__(depth=6)

		self._defaultFunction = defaultFunction
		self._mapping = mapping
		self._state = 'default'
		self._mapping.update({'default': defaultFunction})
		self._mapping.move_to_end('default', last=False)


	def onDialog(self, intent: Intent, session: DialogSession):
		if not session.previousIntent:
			self._state = tuple(self._mapping)[1]

		if session.previousIntent in self._mapping:
			self._state = str(intent)

			try:
				self._mapping[str(session.previousIntent)](intent, session)
			except Exception as e:
				self.logError(f"Can't continue dialog for intent {intent}, method to call for previous intent {session.previousIntent} not found")
