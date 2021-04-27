#  Copyright (c) 2021
#
#  This file, SnipsWakeword.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:48 CEST

import threading

import subprocess
import time
from pathlib import Path
from typing import Optional

from core.voice.model.WakewordEngine import WakewordEngine


class SnipsWakeword(WakewordEngine):

	NAME = 'Snips hotword'
	DEPENDENCIES = {
		'system': [
			'snips-hotword',
			'snips-hotword-model-heysnipsv4'
		],
		'pip': []
	}


	def __init__(self):
		super().__init__()
		self._thread: Optional[threading.Thread] = None
		self._flag = threading.Event()


	def run(self):
		cmd = f'snips-hotword --assistant {self.Commons.rootDir()}/assistant --mqtt {self.ConfigManager.getAliceConfigByName("mqttHost")}:{self.ConfigManager.getAliceConfigByName("mqttPort")}'

		if self.ConfigManager.getAliceConfigByName('monoWakewordEngine'):
			cmd += ' --audio +@mqtt'
		else:
			cmd += f' --audio {self.ConfigManager.getAliceConfigByName("uuid")}@mqtt'

		if self.ConfigManager.getAliceConfigByName('mqttUser'):
			cmd += f' --mqtt-username {self.ConfigManager.getAliceConfigByName("mqttUser")} --mqtt-password {self.ConfigManager.getAliceConfigByName("mqttPassword")}'

		if self.ConfigManager.getAliceConfigByName('mqttTLSFile'):
			cmd += f' --mqtt-tls-cafile {self.ConfigManager.getAliceConfigByName("mqttTLSFile")}'

		cmd += f' --model {self.Commons.rootDir()}/trained/hotwords/snips_hotword/hey_snips={self.ConfigManager.getAliceConfigByName("wakewordSensitivity")}'

		for username in self.UserManager.getAllUserNames():
			if not Path(f'{self.Commons.rootDir()}/trained/hotwords/snips_hotword/{username}').exists():
				continue

			cmd += f' --model {self.Commons.rootDir()}/trained/hotwords/snips_hotword/{username}={self.ConfigManager.getAliceConfigByName("wakewordSensitivity")}'

		process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

		self._flag.set()
		try:
			while self._flag.is_set():
				time.sleep(0.5)
		finally:
			process.terminate()


	def installDependencies(self) -> bool:
		installed = self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', f'{self.Commons.rootDir()}/system/snips/snips-hotword_0.64.0_armhf.deb'])
		installed2 = self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', f'{self.Commons.rootDir()}/system/snips/snips-hotword-model-heysnipsv4_0.64.0_armhf.deb'])
		if installed.returncode or installed2.returncode:
			self.logError(f"Couldn't install Snips wakeword: {installed.stderr}")
			return False
		return True


	def onStop(self):
		super().onStop()
		self._flag.clear()
		if self._thread and self._thread.is_alive():
			self.ThreadManager.terminateThread(name='snipsHotword')


	def onStart(self):
		super().onStart()
		self._flag.clear()
		if self._thread and self._thread.is_alive():
			self._thread.join(timeout=5)

		self._thread: threading.Thread = self.ThreadManager.newThread(name='snipsHotword', target=self.run, autostart=False)
		self._thread.start()
