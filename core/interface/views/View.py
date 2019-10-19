from flask_classful import FlaskView

from core.base.SuperManager import SuperManager
from core.util.model.Logger import Logger


class View(FlaskView):

	def __init__(self):
		super().__init__()
		self._langData = self.WebInterfaceManager.langData
		self._logger = Logger(depth=6)


	def logInfo(self, msg: str):
		self._logger.logInfo(msg)


	def logWarning(self, msg: str):
		self._logger.logWarning(msg)


	def logDebug(self, msg: str):
		self._logger.logDebug(msg)


	def logCritical(self, msg: str):
		self._logger.logCritical(msg)


	def logError(self, msg: str):
		self._logger.logError(msg)


	def logFatal(self, msg: str):
		self._logger.logFatal(msg)


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



	@property
	def Commons(self):
		return SuperManager.getInstance().commons
