#  Copyright (c) 2021
#
#  This file, SubprocessManager.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.05.20 at 12:56:48 CEST

import threading
import time
from typing import Callable, Optional

from core.base.model.Manager import Manager
from core.util.model.AliceSubprocess import AliceSubprocess


class SubprocessManager(Manager):

	def __init__(self):
		super().__init__()

		self._subproc = dict()
		self._thread: Optional[threading.Thread] = None
		self._flag = threading.Event()


	def onStart(self):
		self._flag.clear()
		if self._thread and self._thread.is_alive():
			self._thread.join(timeout=5)

		self._thread: threading.Thread = self.ThreadManager.newThread(name='subprocessManager', target=self.run, autostart=False)
		self._thread.start()


	def onStop(self):
		super().onStop()

		for process in self._subproc.values():
			if process.poll() is None:
				process.terminate()

		self._flag.clear()
		if self._thread and self._thread.is_alive():
			self.ThreadManager.terminateThread(name='subprocessManager')


	def isSubprocessAlive(self, name: str) -> bool:
		return self._subproc[name].poll() is None


	def runSubprocess(self, name: str, cmd: str, stoppedCallback: Callable = None, autoRestart: bool = False) -> bool:
		if name in self._subproc and self._subproc[name].process.poll() is None:
			self.logError(f'Tried adding the subprocess {name} twice')
			return False

		self.logInfo(f'Starting the subprocess {name}')
		self._subproc[name] = AliceSubprocess(name=name, cmd=cmd, stoppedCallback=stoppedCallback, autoRestart=autoRestart)
		self._subproc[name].start()
		return True


	def terminateSubprocess(self, name: str) -> bool:
		if name not in self._subproc:
			self.logError(f'Tried terminating the subprocess {name}, but it was not found')
			return False

		# save to tmp to prevent thread reading terminated process and restarting it
		tmp = self._subproc[name].process
		self._subproc.pop(name)
		tmp.terminate()
		tmp.wait()


	def run(self):
		self._flag.set()
		while self._flag.is_set():
			for subproc in self._subproc.values():
				if subproc.process is not None and subproc.process.poll() is not None:
					self.logInfo(f'Subprocess {subproc.name} went defunct')
					subproc.process = None
					# ask for a restart of that process!
					if subproc.autoRestart:
						self.logInfo(f'Restarting Subprocess {subproc.name}')
						subproc.start()

					if subproc.stoppedCallback is not None:
						subproc.stoppedCallback(name=subproc.name)

			time.sleep(0.5)
