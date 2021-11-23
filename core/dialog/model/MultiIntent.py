#  Copyright (c) 2021
#
#  This file, MultiIntent.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:47 CEST

from collections import deque
from dataclasses import dataclass, field
from typing import Deque

from core.dialog.model import DialogSession


@dataclass
class MultiIntent(object):
	session: DialogSession
	processedString: str
	intents: Deque[str] = field(default_factory=deque)


	@property
	def originalString(self) -> str:
		return self.session['payload']['input']


	def addIntent(self, string: str):
		self.intents.append(string)


	def getNextIntent(self) -> str:
		return self.intents.popleft() if self.intents else ''
