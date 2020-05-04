import json
import threading
from pathlib import Path
from threading import Event
from typing import Optional

import re
from importlib_metadata import PackageNotFoundError, version as packageVersion

from core.asr.model.Recorder import Recorder
from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.base.model.Version import Version
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


	def checkDependencies(self) -> bool:
		self.logInfo('Checking dependencies')
		for dep in self.DEPENDENCIES['pip']:
			match = re.match(r'^([a-zA-Z-_]*)(?:([=><]{0,2})([\d.]*)$)', dep)
			if not match:
				continue

			packageName, operator, version = match.groups()
			if not packageName:
				self.logWarning('Wrongly declared PIP requirement')
				continue

			try:
				installedVersion = packageVersion(packageName)
			except PackageNotFoundError:
				self.logWarning(f'Found missing dependencies: {packageName}')
				return False

			if not installedVersion or not operator or not version:
				continue

			version = Version.fromString(version)
			installedVersion = Version.fromString(installedVersion)

			if (operator == '==' and version != installedVersion) or \
					(operator == '>=' and installedVersion < version) or \
					(operator == '>' and (installedVersion < version or installedVersion == version)) or \
					(operator == '<' and (installedVersion > version or installedVersion == version)):

				self.logWarning(f'Dependency "{packageName}" is not conform with version requirements')
				return False

		return True


	def install(self) -> bool:
		self.logInfo('Installing dependencies')

		try:
			for dep in self.DEPENDENCIES['system']:
				self.logInfo(f'Installing "{dep}"')
				self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', dep])
				self.logInfo(f'Installed!')

			for dep in self.DEPENDENCIES['pip']:
				self.logInfo(f'Installing "{dep}"')
				self.Commons.runSystemCommand(['./venv/bin/pip', 'install', dep])
				self.logInfo(f'Installed!')

			return True
		except Exception as e:
			self.logError(f'Installing dependencies failed: {e}')
			return False


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
