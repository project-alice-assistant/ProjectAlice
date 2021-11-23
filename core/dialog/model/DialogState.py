#  Copyright (c) 2021
#
#  This file, DialogState.py, is part of Project Alice.
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

from core.base.SuperManager import SuperManager


class DialogState(object):

	def __init__(self, state: str):
		if ':' not in state:
			caller = SuperManager.getInstance().commons.getFunctionCaller(depth=2)
			state = f'{caller}:{state}'

		self._state = state


	def __eq__(self, other) -> bool:
		if ':' not in other:
			caller = SuperManager.getInstance().commons.getFunctionCaller()
			other = f'{caller}:{other}'

		return self._state == other


	def __ne__(self, other) -> bool:
		return not self.__eq__(other)


	def __repr__(self) -> str:
		return self._state


	def __str__(self) -> str:
		return self._state
