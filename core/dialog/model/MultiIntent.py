import attr
from typing import Deque
from collections import deque

from core.dialog.model import DialogSession

@attr.s(slots=True, auto_attribs=True)
class MultiIntent:
	session: DialogSession
	processedString: str
	originalString: str = attr.ib(init=False)
	@originalString.default
	def _combineVersions(self):
		return self.session['payload']['input']

	intents: Deque[str] = attr.ib(init=False, default=attr.Factory(deque))

	def addIntent(self, string: str):
		self.intents.append(string)


	def getNextIntent(self) -> str:
		return self.intents.popleft() if self.intents else ''
