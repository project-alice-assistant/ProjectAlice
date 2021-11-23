#  Copyright (c) 2021
#
#  This file, Stopwatch.py, is part of Project Alice.
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

import time


class Stopwatch(object):

	def __init__(self, precision: int = 2):
		self._startTime = None
		self._time = None
		self._precision = precision


	@property
	def time(self) -> int:
		if self._time:
			return self._time
		elif self._startTime:
			return time.time() - self._startTime
		else:
			return 0


	def start(self):
		self._startTime = time.time()


	def lap(self) -> float:
		currentTime = time.time()
		startTime = self._startTime
		self._startTime = currentTime
		return currentTime - startTime


	def stop(self) -> int:
		self._time = time.time() - self._startTime
		return self._time


	def __enter__(self):
		self.start()
		return self


	def __exit__(self, tpe, value, tb):
		self.stop()


	def __str__(self) -> str:
		return f'{self.time:.{self._precision}f}'
