from core.dialog.model import DialogSession


class MultiIntent:
	def __init__(self, session: DialogSession, string: str):
		self._originalString = session['payload']['input']
		self._processedString = string
		self._session = session

		self._intents = list()


	def addIntent(self, string: str):
		self._intents.append(string)


	def getNextIntent(self) -> str:
		return self._intents.pop(0) if self._intents else ''


	@property
	def session(self) -> DialogSession:
		return self._session
