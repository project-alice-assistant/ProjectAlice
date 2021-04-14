#  Copyright (c) 2021
#
#  This file, ThreadTimer.py, is part of Project Alice.
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

from dataclasses import dataclass, field
from threading import Timer
from typing import Callable


@dataclass
class ThreadTimer:
	callback: Callable
	args: list = field(default_factory=list)
	kwargs: dict = field(default_factory=dict)
	timer: Timer = None
