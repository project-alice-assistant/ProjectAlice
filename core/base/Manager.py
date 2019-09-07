from typing import Optional

from core.base.SuperManager import SuperManager
from core.commons import commons
from core.commons.model.Singleton import Singleton
from core.dialog.model.DialogSession import DialogSession


class Manager(Singleton):

	def __init__(self, name: str, databaseSchema: dict = None):
		super().__init__(name)
		self._name              = name
		self._databaseSchema    = databaseSchema
		self._isActive          = True

		self._logger.info('Initializing {}'.format(name))


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
			return commons.getFunctionCaller()
		except Exception as e:
			self._logger.error('[{}] Something went wrong retrieving function caller: {}'.format(self.name, e))
			return None


	def onStart(self):
		self._logger.info('Starting {}'.format(self._name))
		return self._initDB()


	def onStop(self):
		self._logger.info('Stopping {}'.format(self._name))


	def _initDB(self):
		if self._databaseSchema:
			return SuperManager.getInstance().databaseManager.initDB(schema=self._databaseSchema, callerName=self.name)
		return True


	def databaseFetch(self, tableName: str, query: str, values: dict = None, method: str = 'one') -> list:
		return SuperManager.getInstance().databaseManager.fetch(tableName=tableName, query=query, values=values, callerName=self.name, method=method)


	def databaseInsert(self, tableName: str, query: str, values: dict = None) -> int:
		return SuperManager.getInstance().databaseManager.insert(tableName=tableName, query=query, values=values, callerName=self.name)


	def pruneTable(self, tableName: str):
		return SuperManager.getInstance().databaseManager.prune(tableName=tableName, callerName=self.name)


	def onBooted(self): pass
	def onFullMinute(self): pass
	def onFiveMinute(self): pass
	def onQuarterHour(self): pass
	def onFullHour(self): pass
	def onDeviceConnecting(self, *args): pass
	def onDeviceDisconnecting(self, *args): pass
	def onInternetConnected(self, *args): pass
	def onInternetLost(self, *args): pass
	def onHotword(self, siteId: str, session: DialogSession): pass
	def onSessionStarted(self, session: DialogSession): pass
	def onStartListening(self, session: DialogSession): pass
	def onCaptured(self, session: DialogSession): pass
	def onIntentParsed(self, session: DialogSession): pass
	def onUserCancel(self, session: DialogSession): pass
	def onSessionTimeout(self, session: DialogSession): pass
	def onIntentNotRecognized(self, session: DialogSession): pass
	def onSessionError(self, session: DialogSession): pass
	def onSessionEnded(self, session: DialogSession): pass
	def onSay(self, session: DialogSession): pass
	def onSayFinished(self, session: DialogSession): pass
	def onSessionQueued(self, session: DialogSession): pass
