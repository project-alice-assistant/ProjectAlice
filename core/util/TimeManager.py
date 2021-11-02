#  Copyright (c) 2021
#
#  This file, TimeManager.py, is part of Project Alice.
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

from datetime import datetime

from core.base.model.Manager import Manager
from core.commons import constants


class TimeManager(Manager):

	def __init__(self):
		super().__init__()


	def onBooted(self):
		self.timerSignal(1, constants.EVENT_FULL_MINUTE)
		self.timerSignal(5, constants.EVENT_FIVE_MINUTE)
		self.timerSignal(15, constants.EVENT_QUARTER_HOUR)
		self.timerSignal(60, constants.EVENT_FULL_HOUR)


	def timerSignal(self, minutes: int, signal: str, running: bool = False):
		if running:
			self.broadcast(signal, exceptions=[self.name], propagateToSkills=True)

		minute = datetime.now().minute
		second = datetime.now().second
		missingSeconds = 60 * (minutes - minute % minutes) - second
		self.ThreadManager.doLater(interval=missingSeconds, func=self.timerSignal, args=[minutes, signal, True])
