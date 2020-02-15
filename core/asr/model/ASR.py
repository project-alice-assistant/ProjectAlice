from pathlib import Path
from threading import Event

from core.asr.model.Recorder import Recorder
from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.dialog.model.DialogSession import DialogSession


class ASR(ProjectAliceObject):
	NAME = 'Generic ASR'
	TIMEOUT = 20


	def __init__(self):
		self._capableOfArbitraryCapture = False
		self._isOnlineASR = False
		self._listening = False
		self._timeout = Event()
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


	def decodeFile(self, filepath: Path, session: DialogSession):
		pass


	def decodeStream(self, recorder: Recorder):
		self._timeout.clear()
		self.ThreadManager.doLater(interval=self.TIMEOUT, func=self.timeout)


	def timeout(self):
		self._timeout.set()
		self.logWarning('ASR timed out')
