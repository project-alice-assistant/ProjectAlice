#  Copyright (c) 2021
#
#  This file, WakewordEngine.py, is part of Project Alice.
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

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants


class WakewordEngine(ProjectAliceObject):
	NAME = constants.UNKNOWN


	def __init__(self):
		super().__init__()
		self._enabled = True


	def onStart(self):
		self.logInfo(f'Starting **{self.NAME}**')
		self._enabled = True


	def onStop(self, **kwargs):
		self.logInfo(f'Stopping **{self.NAME}**')
		self._enabled = False


	@property
	def enabled(self) -> bool:
		return self._enabled


	@enabled.setter
	def enabled(self, value: bool):
		self._enabled = value
