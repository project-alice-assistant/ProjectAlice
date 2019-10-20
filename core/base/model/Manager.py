import typing
from typing import Optional

from paho.mqtt.client import MQTTMessage

from core.base.SuperManager import SuperManager
from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.dialog.model.DialogSession import DialogSession


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


	def broadcast(self, method, exceptions: list = None, manager = None, propagateToModules: bool = False, silent: bool = False, *args, **kwargs):
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


	def onBooted(self): pass


	# noinspection PyUnusedLocal,PyMethodMayBeStatic
	def onMessage(self, intent: str, session: DialogSession) -> bool: return False
	def onModuleInstalled(self): pass
	def onModuleUpdated(self): pass
	def onFullMinute(self): pass
	def onFiveMinute(self): pass
	def onQuarterHour(self): pass
	def onFullHour(self): pass
	def onDeviceConnecting(self): pass
	def onDeviceDisconnecting(self): pass
	def onInternetConnected(self): pass
	def onInternetLost(self): pass
	def onHotword(self, siteId: str): pass
	def onHotwordToggleOn(self, siteId: str): pass
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
	def onAudioFrame(self, message: MQTTMessage): pass
	def onSnipsAssistantDownloaded(self, **kwargs): pass
	def onSnipsAssistantInstalled(self, **kwargs): pass
	def onSnipsAssistantFailedInstalling(self, **kwargs): pass
	def onUVIndexAlert(self, deviceList: list): pass
	def onRaining(self, deviceList: list): pass
	def onTooMuchRain(self, deviceList: list): pass
	def onWindy(self, deviceList: list): pass
	def onFreezing(self, deviceList: list): pass
	def onTemperatureHighAlert(self, deviceList: list): pass
	def onTemperatureLowAlert(self, deviceList: list): pass
	def onCO2Alert(self, deviceList: list): pass
	def onHumidityHighAlert(self, deviceList: list): pass
	def onHumidityLowAlert(self, deviceList: list): pass
	def onNoiseAlert(self, deviceList: list): pass
	def onPressureHighAlert(self, deviceList: list): pass
	def onPressureLowAlert(self, deviceList: list): pass


	# HELPERS
	def databaseFetch(self, tableName: str, query: str = None, values: dict = None, method: str = 'one') -> typing.Iterable:
		if not query:
			query = 'SELECT * FROM :__table__'

		return self.DatabaseManager.fetch(tableName=tableName, query=query, values=values, callerName=self.name, method=method)


	def databaseInsert(self, tableName: str, query: str = None, values: dict = None) -> int:
		return self.DatabaseManager.insert(tableName=tableName, query=query, values=values, callerName=self.name)


	def pruneTable(self, tableName: str):
		return self.DatabaseManager.prune(tableName=tableName, callerName=self.name)
