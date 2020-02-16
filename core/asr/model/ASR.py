import threading
from pathlib import Path
from threading import Event
from typing import Optional

from core.asr.model.Recorder import Recorder
from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.dialog.model.DialogSession import DialogSession


class ASR(ProjectAliceObject):
	NAME = 'Generic ASR'
	TIMEOUT = 20


	def __init__(self):
		self._capableOfArbitraryCapture = False
		self._isOnlineASR = False
		self._timeout = Event()
		self._timeoutTimer: Optional[threading.Timer] = None
		super().__init__()


	@property
	def capableOfArbitraryCapture(self) -> bool:
		return self._capableOfArbitraryCapture


	@property
	def isOnlineASR(self) -> bool:
		return self._isOnlineASR


	def onStart(self):
		self.logInfo(f'Starting {self.NAME}')


	def onStop(self):
		self.logInfo(f'Stopping {self.NAME}')


	def decodeFile(self, filepath: Path, session: DialogSession):
		pass


	def decodeStream(self, recorder: Recorder):
		self._timeout.clear()
		self._timeoutTimer = self.ThreadManager.newTimer(interval=self.TIMEOUT, func=self.timeout)


	def end(self, recorder: Recorder):
		recorder.stopRecording()
		if self._timeoutTimer and self._timeoutTimer.is_alive():
			self._timeoutTimer.cancel()


	def timeout(self):
		self._timeout.set()
		self.logWarning('ASR timed out')
