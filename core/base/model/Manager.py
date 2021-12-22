#  Copyright (c) 2021
#
#  This file, Manager.py, is part of Project Alice.
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

from typing import Any, Dict, List, Optional

from core.base.SuperManager import SuperManager
from core.base.model.ProjectAliceObject import ProjectAliceObject


class Manager(ProjectAliceObject):

	def __init__(self, name: str = '', databaseSchema: dict = None):
		super().__init__()

		self._name = self.Commons.getFunctionCaller(depth=2) if not name else name
		self._databaseSchema = databaseSchema
		self._isActive = True

		self.logInfo(f'--Initializing--')


	@property
	def name(self):
		return self._name


	@property
	def isActive(self) -> bool:
		return self._isActive


	@isActive.setter
	def isActive(self, value: bool):
		self._isActive = value


	def getMethodCaller(self, **kwargs):
		"""
		Used to print out the calling methods to aid in diagnosing code flow.

		:params methodParam: Can call any or no additional parameters to print out those values
		:return Syslog debug messages
		"""
		if self.ConfigManager.getAliceConfigByName('methodTracing'):
			try:
				return self.Commons.getMethodCaller()
			except Exception as e:
				self.logError(f'Something went wrong retrieving method caller: {e}')


	def getFunctionCaller(self) -> Optional[str]:
		try:
			return self.Commons.getFunctionCaller()
		except Exception as e:
			self.logError(f'Something went wrong retrieving function caller: {e}')
			return None


	def onStart(self):
		self.logInfo(f'Starting')
		self._isActive = True
		return self._initDB()


	def onStop(self):
		self.logInfo(f'Stopping')
		self._isActive = False


	def restart(self):
		"""
		Stops and starts the manager
		:return:
		"""
		self.onStop()
		self.onStart()


	def _initDB(self):
		if self._databaseSchema:
			return SuperManager.getInstance().DatabaseManager.initDB(schema=self._databaseSchema, callerName=self.name)
		return True


	# HELPERS
	def databaseFetch(self, tableName: str, query: str = None, values: dict = None) -> List[Dict[str, Any]]:
		if not query:
			query = 'SELECT * FROM :__table__'

		return self.DatabaseManager.fetch(tableName=tableName, query=query, values=values, callerName=self.name)


	def databaseInsert(self, tableName: str, query: str = None, values: dict = None) -> int:
		return self.DatabaseManager.insert(tableName=tableName, query=query, values=values, callerName=self.name)


	def pruneTable(self, tableName: str):
		return self.DatabaseManager.prune(tableName=tableName, callerName=self.name)
