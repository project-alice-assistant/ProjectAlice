#  Copyright (c) 2021
#
#  This file, SuperManager.py, is part of Project Alice.
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
#  Last modified: 2021.05.24 at 12:56:46 CEST

import subprocess
from typing import Callable


class AliceSubprocess(object):

	def __init__(self, name: str, cmd: str, stoppedCallback: Callable, autoRestart: bool):
		self.name = name
		self.cmd = cmd
		self.stoppedCallback = stoppedCallback
		self.autoRestart = autoRestart
		self.process = None


	def start(self):
		self.process = subprocess.Popen(self.cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
