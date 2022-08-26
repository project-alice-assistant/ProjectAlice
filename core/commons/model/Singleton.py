#  Copyright (c) 2021
#
#  This file, Singleton.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:46 CEST

from core.util.model.Logger import Logger


class Singleton(object):
	INSTANCE = None


	def __init__(self, name):
		super().__init__()

		if self.INSTANCE:
			Logger().logFatal(f'Trying to instanciate {name} but instance already exists')
			raise KeyboardInterrupt
		else:
			self.INSTANCE = self


	@staticmethod
	def getInstance():
		return Singleton.INSTANCE
