#  Copyright (c) 2021
#
#  This file, ContextManagers.py, is part of Project Alice.
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

from contextlib import contextmanager

from core.ProjectAliceExceptions import OfflineError
from core.base.SuperManager import SuperManager


@contextmanager
def Online():  # NOSONAR
	internetManager = SuperManager.getInstance().InternetManager
	if internetManager.online:
		try:
			yield
		except:
			if not internetManager.checkOnlineState():
				raise
			else:
				yield

	raise OfflineError
