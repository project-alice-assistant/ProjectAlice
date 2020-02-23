import subprocess
import time
from pathlib import Path

import re
import tempfile
# noinspection PyUnresolvedReferences
from fcntl import F_GETFL, F_SETFL, fcntl
# noinspection PyUnresolvedReferences
from os import O_NONBLOCK

from core.base.model.Manager import Manager


class SnipsWatchManager(Manager):

	def __init__(self):
		super().__init__()
		self._counter = 0
		self._thread = None
		self._file = Path(tempfile.gettempdir(), 'snipswatch')
		self._lastCheck = 0


	def startWatching(self, verbosity: int = 0):
		self._lastCheck = int(time.time())
		self.stopWatching()

		self._counter = 0
		if self._file.exists():
			self._file.unlink()

		flag = self.ThreadManager.newEvent('snipswatchrunning')
		flag.set()
		self._thread = self.ThreadManager.newThread(
			name='snipswatch',
			target=self.watch,
			args=[verbosity],
			autostart=True
		)


	def watch(self, verbosity: int = 0):
		flag = self.ThreadManager.getEvent('snipswatchrunning')

		arg = ' -' + verbosity * 'v' if verbosity > 0 else ''
		process = subprocess.Popen(f'snips-watch {arg} --html', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

		# This makes stdout.readline non blocking!
		flags = fcntl(process.stdout, F_GETFL)
		fcntl(process.stdout, F_SETFL, flags | O_NONBLOCK)

		while flag.isSet():
			out = process.stdout.readline().decode() or ''
			if out:
				with open(self._file, 'a+') as fp:
					line = out.replace('<b><font color=#009900>', '<b><font color="green">').replace('#009900', '"yellow"').replace('#0000ff', '"green"')
					line = re.sub('<s>(.*?)</s>', '\\1', line)
					fp.write(line)

			if int(time.time()) - 5 > self._lastCheck:
				# Don't let snipswatch run for nothing.
				flag.clear()

			time.sleep(0.1)

		process.kill()


	def stopWatching(self):
		self.ThreadManager.getEvent('snipswatchrunning').clear()
		self.ThreadManager.terminateThread('snipswatch')


	def setVerbosity(self, verbosity: int):
		self.startWatching(verbosity)


	def getLogs(self) -> list:
		# _lastCheck is set to current timestamp everytime the interface asks for logs. If user changes page, it won't be updated anymore
		# and thus snipswatch will be terminated
		self._lastCheck = int(time.time())
		try:
			data = self._file.open('r').readlines()
			ret = data[self._counter:]
			self._counter = len(data)
			return ret
		except:
			return list()
