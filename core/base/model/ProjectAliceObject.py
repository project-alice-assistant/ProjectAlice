import core.base.SuperManager as SM
from core.util.model.Logger import Logger


class ProjectAliceObject(Logger):

	def __init__(self, logDepth: int = 3, *args, **kwargs):
		super().__init__(depth=logDepth)


	def onStart(self): pass
	def onStop(self): pass
	def onBooted(self): pass
	def onModuleInstalled(self): pass
	def onModuleUpdated(self): pass
	def onInternetConnected(self): pass
	def onInternetLost(self): pass
	def onHotword(self, siteId: str): pass
	def onHotwordToggleOn(self, siteId: str): pass
	def onSessionStarted(self, session): pass
	def onStartListening(self, session): pass
	def onCaptured(self, session): pass
	def onIntentParsed(self, session): pass
	def onUserCancel(self, session): pass
	def onSessionTimeout(self, session): pass
	def onIntentNotRecognized(self, session): pass
	def onSessionError(self, session): pass
	def onSessionEnded(self, session): pass
	def onSay(self, session): pass
	def onSayFinished(self, session): pass
	def onSessionQueued(self, session): pass
	def onMessage(self, intent: str, session): pass
	def onSleep(self): pass
	def onWakeup(self): pass
	def onGoingBed(self): pass
	def onLeavingHome(self): pass
	def onReturningHome(self): pass
	def onEating(self): pass
	def onWatchingTV(self): pass
	def onCooking(self): pass
	def onMakeup(self): pass
	def onContextSensitiveDelete(self, sessionId: str): pass
	def onContextSensitiveEdit(self, sessionId: str): pass
	def onFullMinute(self): pass
	def onFiveMinute(self): pass
	def onQuarterHour(self): pass
	def onFullHour(self): pass
	def onCancel(self): pass
	def onASRCaptured(self): pass
	def onWakeword(self): pass
	def onMotionDetected(self): pass
	def onMotionStopped(self): pass
	def onButtonPressed(self): pass
	def onButtonReleased(self): pass
	def onDeviceConnecting(self): pass
	def onDeviceDisconnecting(self): pass
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
	def onBroadcastingForNewDeviceStart(self, session): pass
	def onBroadcastingForNewDeviceStop(self): pass
	def onSnipsAssistantDownloaded(self, **kwargs): pass
	def onSnipsAssistantDownloadFailed(self, **kwargs): pass
	def onAuthenticated(self, session): pass
	def onAuthenticationFailed(self, session): pass
	def onAudioFrame(self, message): pass
	def onSnipsAssistantInstalled(self, **kwargs): pass
	def onSnipsAssistantFailedInstalling(self, **kwargs): pass


	@property
	def ConfigManager(self):
		return SM.SuperManager.getInstance().configManager


	@property
	def ModuleManager(self):
		return SM.SuperManager.getInstance().moduleManager


	@property
	def DeviceManager(self):
		return SM.SuperManager.getInstance().deviceManager


	@property
	def DialogSessionManager(self):
		return SM.SuperManager.getInstance().dialogSessionManager


	@property
	def MultiIntentManager(self):
		return SM.SuperManager.getInstance().multiIntentManager


	@property
	def ProtectedIntentManager(self):
		return SM.SuperManager.getInstance().protectedIntentManager


	@property
	def MqttManager(self):
		return SM.SuperManager.getInstance().mqttManager


	@property
	def SamkillaManager(self):
		return SM.SuperManager.getInstance().samkillaManager


	@property
	def SnipsConsoleManager(self):
		return SM.SuperManager.getInstance().snipsConsoleManager


	@property
	def SnipsServicesManager(self):
		return SM.SuperManager.getInstance().snipsServicesManager


	@property
	def UserManager(self):
		return SM.SuperManager.getInstance().userManager


	@property
	def DatabaseManager(self):
		return SM.SuperManager.getInstance().databaseManager


	@property
	def InternetManager(self):
		return SM.SuperManager.getInstance().internetManager


	@property
	def TelemetryManager(self):
		return SM.SuperManager.getInstance().telemetryManager


	@property
	def ThreadManager(self):
		return SM.SuperManager.getInstance().threadManager


	@property
	def TimeManager(self):
		return SM.SuperManager.getInstance().timeManager


	@property
	def ASRManager(self):
		return SM.SuperManager.getInstance().asrManager


	@property
	def LanguageManager(self):
		return SM.SuperManager.getInstance().languageManager


	@property
	def TalkManager(self):
		return SM.SuperManager.getInstance().talkManager


	@property
	def TTSManager(self):
		return SM.SuperManager.getInstance().ttsManager


	@property
	def WakewordManager(self):
		return SM.SuperManager.getInstance().wakewordManager


	@property
	def WebInterfaceManager(self):
		return SM.SuperManager.getInstance().webInterfaceManager


	@property
	def Commons(self):
		return SM.SuperManager.getInstance().commons
