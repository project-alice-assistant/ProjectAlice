from typing import Optional

from core.base.SuperManager import SuperManager
from core.base.model.ProjectAliceObject import ProjectAliceObject


class Manager(ProjectAliceObject):

	def __init__(self, name: str, databaseSchema: dict = None):
		super().__init__(logDepth=3)

		self._name              = name
		self._databaseSchema    = databaseSchema
		self._isActive          = True

		self.logInfo(f'Initializing {name}')


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
		self.logInfo(f'Starting {self.name}')
		return self._initDB()


	def onStop(self):
		self.logInfo(f'Stopping {self.name}')


	def _initDB(self):
		if self._databaseSchema:
			return SuperManager.getInstance().databaseManager.initDB(schema=self._databaseSchema, callerName=self.name)
		return True


	def broadcast(self, method: str, exceptions: list = None, manager = None, propagateToModules: bool = False, silent: bool = False, *args, **kwargs):
		if not exceptions:
			exceptions = list()

		if not exceptions and not manager:
			self._logger.logWarning('Cannot broadcast to itself, the calling method has to be put in exceptions')

		if 'ProjectAlice' not in exceptions:
			exceptions.append('ProjectAlice')

		deadManagers = list()
		for name, man in SuperManager.getInstance().managers.items():
			if not man:
				deadManagers.append(name)
				continue

			if (manager and man.name != manager.name) or man.name in exceptions:
				continue

			try:
				func = getattr(man, method)
				func(*args, **kwargs)
			except AttributeError as e:
				if not silent:
					self._logger.logWarning(f"Couldn't find method {method} in manager {man.name}: {e}")
			except TypeError:
				# Do nothing, it's most prolly kwargs
				pass

		if propagateToModules:
			self.ModuleManager.broadcast(method=method, silent=silent, *args, **kwargs)

		for name in deadManagers:
			del SuperManager.getInstance().managers[name]


	# HELPERS
	def databaseFetch(self, tableName: str, query: str = None, values: dict = None, method: str = 'one') -> list:
		if not query:
			query = 'SELECT * FROM :__table__'

		return self.DatabaseManager.fetch(tableName=tableName, query=query, values=values, callerName=self.name, method=method)


	def databaseInsert(self, tableName: str, query: str = None, values: dict = None) -> int:
		return self.DatabaseManager.insert(tableName=tableName, query=query, values=values, callerName=self.name)


	def pruneTable(self, tableName: str):
		return self.DatabaseManager.prune(tableName=tableName, callerName=self.name)
