from typing import Optional

from paho.mqtt.client import MQTTMessage

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

		self._logger.info(f'Initializing {name}')


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
			self._logger.error(f'[{self.name}] Something went wrong retrieving function caller: {e}')
			return None


	def onStart(self, *args: tuple, **kwargs: dict):
		self._logger.info(f'Starting {self.name}')
		return self._initDB()


	def onStop(self, *args: tuple, **kwargs: dict):
		self._logger.info(f'Stopping {self.name}')


	def _initDB(self):
		if self._databaseSchema:
			return SuperManager.getInstance().databaseManager.initDB(schema=self._databaseSchema, callerName=self.name)
		return True


	def onBooted(self, *args: tuple, **kwargs: dict): pass
	def onModuleInstalled(self, *args: tuple, **kwargs: dict): pass
	def onModuleUpdated(self, *args: tuple, **kwargs: dict): pass
	def onFullMinute(self, *args: tuple, **kwargs: dict): pass
	def onFiveMinute(self, *args: tuple, **kwargs: dict): pass
	def onQuarterHour(self, *args: tuple, **kwargs: dict): pass
	def onFullHour(self, *args: tuple, **kwargs: dict): pass
	def onDeviceConnecting(self, *args: tuple, **kwargs: dict): pass
	def onDeviceDisconnecting(self, *args: tuple, **kwargs: dict): pass
	def onInternetConnected(self, *args: tuple, **kwargs: dict): pass
	def onInternetLost(self, *args: tuple, **kwargs: dict): pass
	def onHotword(self, session: DialogSession, *args: tuple, **kwargs: dict): pass
	def onHotwordToggleOn(self, session: DialogSession, *args: tuple, **kwargs: dict):pass
	def onSessionStarted(self, session: DialogSession, *args: tuple, **kwargs: dict): pass
	def onStartListening(self, session: DialogSession, *args: tuple, **kwargs: dict): pass
	def onCaptured(self, session: DialogSession, *args: tuple, **kwargs: dict): pass
	def onIntentParsed(self, session: DialogSession, *args: tuple, **kwargs: dict): pass
	def onUserCancel(self, session: DialogSession, *args: tuple, **kwargs: dict): pass
	def onSessionTimeout(self, session: DialogSession, *args: tuple, **kwargs: dict): pass
	def onIntentNotRecognized(self, session: DialogSession, *args: tuple, **kwargs: dict): pass
	def onSessionError(self, session: DialogSession, *args: tuple, **kwargs: dict): pass
	def onSessionEnded(self, session: DialogSession, *args: tuple, **kwargs: dict): pass
	def onSay(self, session: DialogSession, *args: tuple, **kwargs: dict): pass
	def onSayFinished(self, session: DialogSession, *args: tuple, **kwargs: dict): pass
	def onSessionQueued(self, session: DialogSession, *args: tuple, **kwargs: dict): pass
	def onAudioFrame(self, message: MQTTMessage, *args: tuple, **kwargs: dict): pass
	def onSnipsAssistantDownloaded(self, *args: tuple, **kwargs: dict): pass


	# HELPERS
	def databaseFetch(self, tableName: str, query: str = None, values: dict = None, method: str = 'one') -> list:
		if not query:
			query = 'SELECT * FROM :__table__'

		return self.DatabaseManager.fetch(tableName=tableName, query=query, values=values, callerName=self.name, method=method)


	def databaseInsert(self, tableName: str, query: str, values: dict = None) -> int:
		return self.DatabaseManager.insert(tableName=tableName, query=query, values=values, callerName=self.name)


	def pruneTable(self, tableName: str):
		return self.DatabaseManager.prune(tableName=tableName, callerName=self.name)


	@property
	def ConfigManager(self):
		return SuperManager.getInstance().configManager


	@property
	def ModuleManager(self):
		return SuperManager.getInstance().moduleManager


	@property
	def DeviceManager(self):
		return SuperManager.getInstance().deviceManager


	@property
	def DialogSessionManager(self):
		return SuperManager.getInstance().dialogSessionManager


	@property
	def MultiIntentManager(self):
		return SuperManager.getInstance().multiIntentManager


	@property
	def ProtectedIntentManager(self):
		return SuperManager.getInstance().protectedIntentManager


	@property
	def MqttManager(self):
		return SuperManager.getInstance().mqttManager


	@property
	def SamkillaManager(self):
		return SuperManager.getInstance().samkillaManager


	@property
	def SnipsConsoleManager(self):
		return SuperManager.getInstance().snipsConsoleManager


	@property
	def SnipsServicesManager(self):
		return SuperManager.getInstance().snipsServicesManager


	@property
	def UserManager(self):
		return SuperManager.getInstance().userManager


	@property
	def DatabaseManager(self):
		return SuperManager.getInstance().databaseManager


	@property
	def InternetManager(self):
		return SuperManager.getInstance().internetManager


	@property
	def TelemetryManager(self):
		return SuperManager.getInstance().telemetryManager


	@property
	def ThreadManager(self):
		return SuperManager.getInstance().threadManager


	@property
	def TimeManager(self):
		return SuperManager.getInstance().timeManager


	@property
	def ASRManager(self):
		return SuperManager.getInstance().ASRManager


	@property
	def LanguageManager(self):
		return SuperManager.getInstance().languageManager


	@property
	def TalkManager(self):
		return SuperManager.getInstance().talkManager


	@property
	def TTSManager(self):
		return SuperManager.getInstance().TTSManager


	@property
	def WakewordManager(self):
		return SuperManager.getInstance().wakewordManager

	@property
	def WebInterfaceManager(self):
		return SuperManager.getInstance().webInterfaceManager
