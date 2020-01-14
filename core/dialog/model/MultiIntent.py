from dataclasses import dataclass, field
from typing import Deque
from collections import deque

from core.dialog.model import DialogSession

@dataclass
class MultiIntent:
	session: DialogSession
	processedString: str
	intents: Deque[str] = field(default_factory=deque)

	@property
	def originalString(self) -> str:
		return self.session['payload']['input']


	def addIntent(self, string: str):
		self.intents.append(string)


	def getNextIntent(self) -> str:
		return self.intents.popleft() if self.intents else ''
