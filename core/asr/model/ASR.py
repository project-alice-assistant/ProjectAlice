from pathlib import Path

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.dialog.model.DialogSession import DialogSession


class ASR(ProjectAliceObject):
	NAME = 'Generic ASR'


	def __init__(self):
		self._capableOfArbitraryCapture = False
		self._isOnlineASR = False
		self._listening = False
		super().__init__()


	@property
	def capableOfArbitraryCapture(self) -> bool:
		return self._capableOfArbitraryCapture


	@property
	def isOnlineASR(self) -> bool:
		return self._isOnlineASR


	def onStart(self):
		self.logInfo(f'Started {self.NAME}')


	def onStop(self):
		self.logInfo(f'Stopped {self.NAME}')


	def onStartListening(self, session: DialogSession):
		self._listening = True


	@property
	def isListening(self) -> bool:
		return self._listening


	def onCaptured(self, session: DialogSession):
		self._listening = False


	def decode(self, filepath: Path, session: DialogSession):
		pass
