#  Copyright (c) 2021
#
#  This file, StateManager.py, is part of Project Alice.
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

from typing import Optional

from core.ProjectAliceExceptions import StateAlreadyRegistered
from core.base.model.Manager import Manager
from core.base.model.State import State
from core.base.model.StateType import StateType


class StateManager(Manager):
	"""
	Managing any state for anything. This manager keeps track of whatever state you want to
	keep track of.
	"""

	def __init__(self):
		super().__init__()
		self._states = dict()


	def onStop(self):
		super().onStop()
		for state in self.allStates():
			state.setState(StateType.STOPPED)


	@property
	def states(self) -> dict:
		return self._states


	def register(self, statePath: str, initialState: StateType = StateType.BORN) -> Optional[State]:
		"""
		Register a new state
		:param statePath: If containing "." it will be distributed as a dict
		:param initialState: sets the initialstate
		:return: State
		"""

		try:
			state = State(statePath.split('.')[-1], initialState)
			self._buildDict(statePath, state)
			return state
		except StateAlreadyRegistered:
			return None


	def _buildDict(self, statePath: str, state: State):
		"""
		Generates a dict from a dotted string
		:param statePath: dotted string
		:param state: state name
		"""
		track = self._states
		parts = statePath.split('.')
		for i, path in enumerate(parts):
			if i + 1 == len(parts):
				if path in track:
					raise StateAlreadyRegistered('Already declared state')
				else:
					track[path] = state
					return
			else:
				if isinstance(track.get(path, dict()), State):
					raise StateAlreadyRegistered('Already declared state path')
				else:
					track = track.setdefault(path, dict())


	def getState(self, statePath: str) -> Optional[State]:
		"""
		Returns a registered state on the given path, if any
		:param statePath: path
		:return: State
		"""
		track = self._states
		parts = statePath.split('.')
		try:
			for i, path in enumerate(parts):
				if i + 1 == len(parts):
					ret = track.get(path)
					if not isinstance(ret, State):
						return None
					else:
						return ret
				else:
					track = track[path]
		except KeyError:
			return None


	def setState(self, statePath: str, newState: StateType) -> bool:
		"""
		Sets a given state's current state
		:param statePath: dotted string
		:param newState: the new state to seet
		:return: true is state exists
		"""
		state = self.getState(statePath)
		if not state:
			return False

		state.setState(newState)
		return True


	def allStates(self, states: dict = None, found: list = None):
		"""
		Returns all know registered states, recursively
		"""
		if states is None:
			states = self._states

		if found is None:
			found = list()

		for key, item in states.items():
			if isinstance(item, dict):
				self.allStates(item, found)
			else:
				found.append(item)

		return found
