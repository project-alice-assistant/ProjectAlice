import json
import threading
from pathlib import Path
from threading import Event
from typing import Optional

from core.asr.model.Recorder import Recorder
from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class Asr(ProjectAliceObject):
	NAME = 'Generic Asr'
	DEPENDENCIES = dict()


	def __init__(self):
		self._capableOfArbitraryCapture = False
		self._isOnlineASR = False
		self._timeout = Event()
		self._timeoutTimer: Optional[threading.Timer] = None
		self._recorder: Optional[Recorder] = None
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
		self._timeout.set()


	def decodeFile(self, filepath: Path, session: DialogSession):
		# We do not yet use decode file, but might at one point
		pass


	def decodeStream(self, session: DialogSession):
		self._timeout.clear()
		self._timeoutTimer = self.ThreadManager.newTimer(interval=int(self.ConfigManager.getAliceConfigByName('asrTimeout')), func=self.timeout)


	def end(self):
		self._recorder.stopRecording()
		if self._timeoutTimer and self._timeoutTimer.is_alive():
			self._timeoutTimer.cancel()


	def timeout(self):
		self._timeout.set()
		self.logWarning('Asr timed out')


	def checkLanguage(self) -> bool:
		return True


	def downloadLanguage(self) -> bool:
		return False


	def partialTextCaptured(self, session: DialogSession, text: str, likelihood: float, seconds: float):
		self.MqttManager.publish(constants.TOPIC_PARTIAL_TEXT_CAPTURED, json.dumps({
			'text'      : text,
			'likelihood': likelihood,
			'seconds'   : seconds,
			'siteId'    : session.siteId,
			'sessionId' : session.sessionId
		}))
