from typing import Optional

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


	def getFunctionCaller(self) -> Optional[str]:
		try:
			return self.Commons.getFunctionCaller()
		except Exception as e:
			self.logError(f'Something went wrong retrieving function caller: {e}')
			return None


	def onStart(self):
		self.logInfo(f'Starting')
		return self._initDB()


	def onStop(self):
		self.logInfo(f'Stopping')


	def _initDB(self):
		if self._databaseSchema:
			return SuperManager.getInstance().databaseManager.initDB(schema=self._databaseSchema, callerName=self.name)
		return True


	# HELPERS
	def databaseFetch(self, tableName: str, query: str = None, values: dict = None, method: str = 'one') -> list:
		if not query:
			query = 'SELECT * FROM :__table__'

		return self.DatabaseManager.fetch(tableName=tableName, query=query, values=values, callerName=self.name, method=method)


	def databaseInsert(self, tableName: str, query: str = None, values: dict = None) -> int:
		return self.DatabaseManager.insert(tableName=tableName, query=query, values=values, callerName=self.name)


	def pruneTable(self, tableName: str):
		return self.DatabaseManager.prune(tableName=tableName, callerName=self.name)
