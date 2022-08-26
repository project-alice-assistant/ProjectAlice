#  Copyright (c) 2021
#
#  This file, InternetManager.py, is part of Project Alice.
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
#  Last modified: 2021.07.31 at 15:54:28 CEST

import requests

from core.base.model.Manager import Manager
from core.commons import constants


class InternetManager(Manager):

	def __init__(self):
		super().__init__()
		self._online = False
		self._checkThread = None
		self._checkFrequency = 2


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('stayCompletelyOffline'):
			self.checkOnlineState(silent=True)
			# 20 seconds is the max, 2 seconds the minimum
			# We have 10 positions in the config (from 1 to 10) So the frequency = max / 10 * setting = 2 * setting
			internetQuality = self.ConfigManager.getAliceConfigByName('internetQuality') or 1
			self._checkFrequency = internetQuality * 2
			self._checkThread = self.ThreadManager.newThread(name='internetCheckThread', target=self.checkInternet)
		else:
			self.logInfo('Configurations set to stay completely offline')


	@property
	def online(self) -> bool:
		return self._online


	def onBooted(self):
		self.checkOnlineState()


	def checkInternet(self):
		self.checkOnlineState()
		self.ThreadManager.doLater(interval=self._checkFrequency, func=self.checkInternet)


	def checkOnlineState(self, addr: str = 'https://api.projectalice.io/generate_204', silent: bool = False) -> bool:
		if self.ConfigManager.getAliceConfigByName('stayCompletelyOffline'):
			return False

		try:
			online = requests.get(addr).status_code == 204
		except:
			online = False

		if silent:
			self._online = online
			return online

		if self._online and not online:
			self._online = False
			self.broadcast(method=constants.EVENT_INTERNET_LOST, exceptions=[self.name], propagateToSkills=True)
		elif not self._online and online:
			self._online = True
			self.broadcast(method=constants.EVENT_INTERNET_CONNECTED, exceptions=[self.name], propagateToSkills=True)

		return online
