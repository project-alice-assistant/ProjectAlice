import json

from copy import copy

import core.base.SuperManager as SM
from core.commons import constants
from core.util.model.Logger import Logger


class ProjectAliceObject:

	def __init__(self, *args, **kwargs):
		self._logger = Logger(*args, **kwargs)


	def __repr__(self) -> str:
		ret = copy(self.__dict__)
		ret.pop('_logger')
		return json.dumps(ret)


	def __str__(self) -> str:
		return self.__repr__()


	def broadcast(self, method: str, exceptions: list = None, manager = None, propagateToSkills: bool = False, **kwargs):
		if not exceptions:
			exceptions = list()

		if isinstance(exceptions, str):
			exceptions = [exceptions]

		if not exceptions and not manager:
			# Prevent infinite loop of broadcaster being broadcasted to re broadcasting
			self.logWarning('Cannot broadcast to itself, the calling method has to be put in exceptions')
			return

		if 'ProjectAlice' not in exceptions:
			exceptions.append('ProjectAlice')

		if not method.startswith('on'):
			method = f'on{method[0].capitalize() + method[1:]}'

		deadManagers = list()
		for name, man in SM.SuperManager.getInstance().managers.items():
			if not man:
				deadManagers.append(name)
				continue

			if (manager and man.name != manager.name) or man.name in exceptions:
				continue

			try:
				func = getattr(man, method, None)
				if func:
					func(**kwargs)

			except TypeError as e:
				self.logWarning(f'- Failed to broadcast event {method} to {man.name}: {e}')

		if propagateToSkills:
			self.SkillManager.skillBroadcast(method=method, **kwargs)

		for name in deadManagers:
			del SM.SuperManager.getInstance().managers[name]


	def logInfo(self, msg: str):
		self._logger.doLog(function='info', msg=self.decorateLogs(msg), printStack=False)


	def logError(self, msg: str):
		self._logger.doLog(function='error', msg=self.decorateLogs(msg))


	def logDebug(self, msg: str):
		self._logger.doLog(function='debug', msg=self.decorateLogs(msg), printStack=False)


	def logFatal(self, msg: str):
		self._logger.doLog(function='fatal', msg=self.decorateLogs(msg))
		try:
			self.ProjectAlice.onStop()
		except:
			exit()


	def logWarning(self, msg: str, printStack: bool = False):
		self._logger.doLog(function='warning', msg=self.decorateLogs(msg), printStack=printStack)


	def logCritical(self, msg: str):
		self._logger.doLog(function='critical', msg=self.decorateLogs(msg))


	def decorateLogs(self, text: str) -> str:
		return f'[{self.__class__.__name__}] {text}'


	def onStart(self):
		pass


	def onStop(self):
		pass


	def onBooted(self):
		pass


	def onSkillInstalled(self, skill: str):
		pass


	def onSkillUpdated(self, skill: str):
		pass


	def onInternetConnected(self):
		pass


	def onInternetLost(self):
		pass


	def onHotword(self, siteId: str, user: str = constants.UNKNOWN_USER):
		pass


	def onHotwordToggleOn(self, siteId: str):
		pass


	def onHotwordToggleOff(self, siteId: str):
		pass


	def onSessionStarted(self, session):
		pass


	def onStartListening(self, session):
		pass


	def onStopListening(self, session):
		pass


	def onCaptured(self, session):
		pass


	def onNluQuery(self, session):
		pass


	def onIntentParsed(self, session):
		pass


	def onUserCancel(self, session):
		pass


	def onSessionTimeout(self, session):
		pass


	def onIntentNotRecognized(self, session):
		pass


	def onSessionError(self, session):
		pass


	def onSessionEnded(self, session):
		pass


	def onSay(self, session):
		pass


	def onSayFinished(self, session):
		pass


	def onSessionQueued(self, session):
		pass


	def onMessage(self, session) -> bool:
		""" Do not consume the intent by default """
		return False


	def onSleep(self):
		pass


	def onWakeup(self):
		pass


	def onGoingBed(self):
		pass


	def onLeavingHome(self):
		pass


	def onReturningHome(self):
		pass


	def onEating(self):
		pass


	def onWatchingTV(self):
		pass


	def onCooking(self):
		pass


	def onMakeup(self):
		pass


	def onContextSensitiveDelete(self, session):
		pass


	def onContextSensitiveEdit(self, session):
		pass


	def onFullMinute(self):
		pass


	def onFiveMinute(self):
		pass


	def onQuarterHour(self):
		pass


	def onFullHour(self):
		pass


	def onWakeword(self, siteId: str, user: str = constants.UNKNOWN_USER):
		pass


	def onMotionDetected(self):
		pass


	def onMotionStopped(self):
		pass


	def onButtonPressed(self):
		pass


	def onButtonReleased(self):
		pass


	def onDeviceConnecting(self):
		pass


	def onDeviceDisconnecting(self):
		pass


	def onUVIndexAlert(self, *args, **kwargs):
		pass


	def onRaining(self, *args, **kwargs):
		pass


	def onTooMuchRain(self, *args, **kwargs):
		pass


	def onWindy(self, *args, **kwargs):
		pass


	def onFreezing(self, *args, **kwargs):
		pass


	def onTemperatureHighAlert(self, *args, **kwargs):
		pass


	def onTemperatureLowAlert(self, *args, **kwargs):
		pass


	def onCO2Alert(self, *args, **kwargs):
		pass


	def onHumidityHighAlert(self, *args, **kwargs):
		pass


	def onHumidityLowAlert(self, *args, **kwargs):
		pass


	def onNoiseAlert(self, *args, **kwargs):
		pass


	def onPressureHighAlert(self, *args, **kwargs):
		pass


	def onPressureLowAlert(self, *args, **kwargs):
		pass


	def onBroadcastingForNewDeviceStart(self):
		pass


	def onBroadcastingForNewDeviceStop(self, *args):
		pass


	def onAuthenticated(self, session):
		pass


	def onAuthenticationFailed(self, session):
		pass


	def onAudioFrame(self, **kwargs):
		pass


	def onSnipsAssistantInstalled(self, **kwargs):
		pass


	def onSnipsAssistantFailedTraining(self, **kwargs):
		pass


	def onSkillInstallFailed(self, skill: str):
		pass


	def onNluTrained(self, **kwargs):
		pass


	def onVadUp(self, **kwargs):
		pass


	def onVadDown(self, **kwargs):
		pass


	def onPartialTextCaptured(self, session, text: str, likelihood: float, seconds: float):
		pass


	def onEndSession(self, session):
		pass


	def onDeviceHeartbeat(self, uid: str, siteId: str = None):
		pass


	@property
	def ProjectAlice(self):
		return SM.SuperManager.getInstance().projectAlice


	@property
	def ConfigManager(self):
		return SM.SuperManager.getInstance().configManager


	@property
	def SkillManager(self):
		return SM.SuperManager.getInstance().skillManager


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
		return SM.SuperManager.getInstance().commonsManager


	@property
	def SkillStoreManager(self):
		return SM.SuperManager.getInstance().skillStoreManager


	@property
	def NluManager(self):
		return SM.SuperManager.getInstance().nluManager


	@property
	def DialogTemplateManager(self):
		return SM.SuperManager.getInstance().dialogTemplateManager


	@property
	def SnipsAssistantManager(self):
		return SM.SuperManager.getInstance().snipsAssistantManager


	@property
	def AliceWatchManager(self):
		return SM.SuperManager.getInstance().aliceWatchManager


	@property
	def VadManager(self):
		return SM.SuperManager.getInstance().vadManager
