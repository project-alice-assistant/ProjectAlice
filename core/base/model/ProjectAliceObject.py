import json
from pathlib import Path

import re
from copy import copy
from importlib_metadata import PackageNotFoundError, version as packageVersion

import core.base.SuperManager as SM
from core.base.model.Version import Version
from core.commons import constants
from core.util.model.Logger import Logger


class ProjectAliceObject:
	DEPENDENCIES = {
		'internal': {},
		'external': {},
		'system': [],
		'pip'   : []
	}

	def __init__(self, *args, **kwargs):
		self._logger = Logger(*args, **kwargs)


	def __repr__(self) -> str:
		ret = copy(self.__dict__)
		ret.pop('_logger')
		return json.dumps(ret)


	def __str__(self) -> str:
		return self.__repr__()


	def broadcast(self, method: str, exceptions: list = None, manager = None, propagateToSkills: bool = False, **kwargs): #NOSONAR
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

		if 'DialogManager' not in exceptions:
			exceptions.append('DialogManager')

		if not method.startswith('on'):
			method = f'on{method[0].capitalize() + method[1:]}'

		# Give absolute priority to DialogManager
		try:
			func = getattr(SM.SuperManager.getInstance().getManager('DialogManager'), method, None)
			if func:
				func(**kwargs)

		except TypeError as e:
			self.logWarning(f'- Failed to broadcast event **{method}** to **DialogManager**: {e}')


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
				self.logWarning(f'- Failed to broadcast event **{method}** to **{man.name}**: {e}')

		if propagateToSkills:
			self.SkillManager.skillBroadcast(method=method, **kwargs)

		for name in deadManagers:
			del SM.SuperManager.getInstance().managers[name]


		# Now send the event over mqtt
		payload = dict()
		for item, value in kwargs.items():
			try:
				payload[item] = json.dumps(value)
			except:
				# Cannot serialize that attribute, do nothing
				pass

		self.MqttManager.publish(
			topic=method,
			payload=payload
		)


	def checkDependencies(self) -> bool:
		self.logInfo('Checking dependencies')

		for dep in {**self.DEPENDENCIES.get('internal', dict()), **self.DEPENDENCIES.get('external', dict())}:
			result = self.Commons.runRootSystemCommand(['dpkg-query', '-l', dep])
			if result.returncode:
				self.logWarning(f'Found missing dependency: {dep}')
				return False

		for dep in self.DEPENDENCIES['pip']:
			match = re.match(r'^([a-zA-Z0-9-_]*)(?:([=><]{0,2})([\d.]*)$)', dep)
			if not match:
				continue

			packageName, operator, version = match.groups()
			if not packageName:
				self.logWarning('Wrongly declared PIP requirement')
				continue

			try:
				installedVersion = packageVersion(packageName)
			except PackageNotFoundError:
				self.logWarning(f'Found missing dependencies: {packageName}')
				return False

			if not installedVersion or not operator or not version:
				continue

			version = Version.fromString(version)
			installedVersion = Version.fromString(installedVersion)

			if (operator == '==' and version != installedVersion) or \
					(operator == '>=' and installedVersion < version) or \
					(operator == '>' and (installedVersion < version or installedVersion == version)) or \
					(operator == '<' and (installedVersion > version or installedVersion == version)):

				self.logWarning(f'Dependency "{packageName}" is not conform with version requirements')
				return False

		for dep in self.DEPENDENCIES['system']:
			result = self.Commons.runRootSystemCommand(['dpkg-query', '-l', dep])
			if result.returncode:
				self.logWarning(f'Found missing dependency: {dep}')
				return False

		return True


	def installDependencies(self) -> bool:
		self.logInfo('Installing dependencies')

		try:
			for dep, link in self.DEPENDENCIES.get('internal', dict()).items():
				self.logInfo(f'Installing "{dep}"')
				result = self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', f'./{link}'])
				if result.returncode:
					raise Exception(result.stderr)

				self.logInfo(f'Installed!')

			for dep, link in self.DEPENDENCIES.get('external', dict()).items():
				self.logInfo(f'Downloading "{dep}"')
				if not self.Commons.downloadFile(link, link.rsplit('/')[-1]):
					return False

				self.logInfo(f'Installing "{dep}"')
				result = self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', f'./{link.rsplit("/")[-1]}'])
				if result.returncode:
					raise Exception(result.stderr)

				Path(link.rsplit('/')[-1]).unlink()

				self.logInfo(f'Installed!')

			for dep in self.DEPENDENCIES['system']:
				self.logInfo(f'Installing "{dep}"')
				result = self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', dep])
				if result.returncode:
					raise Exception(result.stderr)

				self.logInfo(f'Installed!')

			for dep in self.DEPENDENCIES['pip']:
				self.logInfo(f'Installing "{dep}"')
				result = self.Commons.runSystemCommand(['./venv/bin/pip', 'install', dep])
				if result.returncode:
					raise Exception(result.stderr)

				self.logInfo(f'Installed!')

			return True
		except Exception as e:
			self.logError(f'Installing dependencies failed: {e}')
			return False


	def logInfo(self, msg: str, plural: str = None):
		self._logger.doLog(function='info', msg=self.decorateLogs(msg), printStack=False, plural=plural)


	def logError(self, msg: str, plural: str = None):
		self._logger.doLog(function='error', msg=self.decorateLogs(msg), plural=plural)


	def logDebug(self, msg: str, plural: str = None):
		self._logger.doLog(function='debug', msg=self.decorateLogs(msg), printStack=False, plural=plural)


	def logFatal(self, msg: str, plural: str = None):
		self._logger.doLog(function='fatal', msg=self.decorateLogs(msg), plural=plural)
		try:
			self.ProjectAlice.onStop()
		except:
			exit()


	def logWarning(self, msg: str, printStack: bool = False, plural: str = None):
		self._logger.doLog(function='warning', msg=self.decorateLogs(msg), printStack=printStack, plural=plural)


	def logCritical(self, msg: str, plural: str = None):
		self._logger.doLog(function='critical', msg=self.decorateLogs(msg), plural=plural)


	def decorateLogs(self, text: str) -> str:
		return f'[{self.__class__.__name__}] {text}'


	def onStart(self):
		pass # Super object function is overriden only if needed


	def onStop(self, **kwargs):
		pass # Super object function is overriden only if needed


	def onBooted(self):
		pass # Super object function is overriden only if needed


	def onSkillInstalled(self, skill: str):
		pass # Super object function is overriden only if needed


	def onSkillDeleted(self, skill: str):
		pass # Super object function is overriden only if needed


	def onSkillUpdated(self, skill: str):
		pass # Super object function is overriden only if needed


	def onInternetConnected(self):
		pass # Super object function is overriden only if needed


	def onInternetLost(self):
		pass # Super object function is overriden only if needed


	def onHotword(self, siteId: str, user: str = constants.UNKNOWN_USER):
		pass # Super object function is overriden only if needed


	def onHotwordToggleOn(self, siteId: str, session):
		pass # Super object function is overriden only if needed


	def onHotwordToggleOff(self, siteId: str, session):
		pass # Super object function is overriden only if needed


	def onSessionStarted(self, session):
		pass # Super object function is overriden only if needed


	def onContinueSession(self, session):
		pass # Super object function is overriden only if needed


	def onAsrToggleOn(self, siteId: str):
		pass # Super object function is overriden only if needed


	def onAsrToggleOff(self, siteId: str):
		pass # Super object function is overriden only if needed


	def onStartListening(self, session):
		pass # Super object function is overriden only if needed


	def onStopListening(self, session):
		pass # Super object function is overriden only if needed


	def onCaptured(self, session):
		pass # Super object function is overriden only if needed


	def onNluQuery(self, session):
		pass # Super object function is overriden only if needed


	def onIntentParsed(self, session):
		pass # Super object function is overriden only if needed


	def onIntent(self, session):
		pass # Super object function is overriden only if needed


	def onConfigureIntent(self, intents: list):
		pass # Super object function is overriden only if needed


	def onUserCancel(self, session):
		pass # Super object function is overriden only if needed


	def onSessionTimeout(self, session):
		pass # Super object function is overriden only if needed


	def onIntentNotRecognized(self, session):
		pass # Super object function is overriden only if needed


	def onNluIntentNotRecognized(self, session):
		pass # Super object function is overriden only if needed


	def onNluError(self, session):
		pass # Super object function is overriden only if needed


	def onSessionError(self, session):
		pass # Super object function is overriden only if needed


	def onStartSession(self, siteId: str, payload: dict):
		pass # Super object function is overriden only if needed


	def onSessionEnded(self, session):
		pass # Super object function is overriden only if needed


	def onSay(self, session):
		pass # Super object function is overriden only if needed


	def onSayFinished(self, session, uid: str = None):
		pass # Super object function is overriden only if needed


	def onSessionQueued(self, session):
		pass # Super object function is overriden only if needed


	def onMessage(self, session) -> bool: #NOSONAR
		""" Do not consume the intent by default """
		return False


	def onSleep(self):
		pass # Super object function is overriden only if needed


	def onWakeup(self):
		pass # Super object function is overriden only if needed


	def onGoingBed(self):
		pass # Super object function is overriden only if needed


	def onLeavingHome(self):
		pass # Super object function is overriden only if needed


	def onReturningHome(self):
		pass # Super object function is overriden only if needed


	def onEating(self):
		pass # Super object function is overriden only if needed


	def onWatchingTV(self):
		pass # Super object function is overriden only if needed


	def onCooking(self):
		pass # Super object function is overriden only if needed


	def onMakeup(self):
		pass # Super object function is overriden only if needed


	def onContextSensitiveDelete(self, session):
		pass # Super object function is overriden only if needed


	def onContextSensitiveEdit(self, session):
		pass # Super object function is overriden only if needed


	def onFullMinute(self):
		pass # Super object function is overriden only if needed


	def onFiveMinute(self):
		pass # Super object function is overriden only if needed


	def onQuarterHour(self):
		pass # Super object function is overriden only if needed


	def onFullHour(self):
		pass # Super object function is overriden only if needed


	def onWakeword(self, siteId: str, user: str = constants.UNKNOWN_USER):
		pass # Super object function is overriden only if needed


	def onMotionDetected(self):
		pass # Super object function is overriden only if needed


	def onMotionStopped(self):
		pass # Super object function is overriden only if needed


	def onButtonPressed(self):
		pass # Super object function is overriden only if needed


	def onButtonReleased(self):
		pass # Super object function is overriden only if needed


	def onDeviceDiscovered(self, device, uid: str):
		pass # Super object function is overriden only if needed


	def onDeviceAdded(self, device, uid: str):
		pass # Super object function is overriden only if needed


	def onDeviceRemoved(self, device, uid: str):
		pass # Super object function is overriden only if needed


	def onDeviceConnecting(self):
		pass # Super object function is overriden only if needed


	def onDeviceDisconnecting(self):
		pass # Super object function is overriden only if needed


	def onUVIndexAlert(self, *args, **kwargs):
		pass # Super object function is overriden only if needed


	def onRaining(self, *args, **kwargs):
		pass # Super object function is overriden only if needed


	def onTooMuchRain(self, *args, **kwargs):
		pass # Super object function is overriden only if needed


	def onWindy(self, *args, **kwargs):
		pass # Super object function is overriden only if needed


	def onFreezing(self, *args, **kwargs):
		pass # Super object function is overriden only if needed


	def onTemperatureHighAlert(self, *args, **kwargs):
		pass # Super object function is overriden only if needed


	def onTemperatureLowAlert(self, *args, **kwargs):
		pass # Super object function is overriden only if needed


	def onCOTwoAlert(self, *args, **kwargs):
		pass # Super object function is overriden only if needed


	def onHumidityHighAlert(self, *args, **kwargs):
		pass # Super object function is overriden only if needed


	def onHumidityLowAlert(self, *args, **kwargs):
		pass # Super object function is overriden only if needed


	def onNoiseAlert(self, *args, **kwargs):
		pass # Super object function is overriden only if needed


	def onPressureHighAlert(self, *args, **kwargs):
		pass # Super object function is overriden only if needed

	def onGasAlert(self, *args, **kwargs):
		pass # Super object function is overriden only if needed

	def onPressureLowAlert(self, *args, **kwargs):
		pass # Super object function is overriden only if needed


	def onBroadcastingForNewDeviceStart(self):
		pass # Super object function is overriden only if needed


	def onBroadcastingForNewDeviceStop(self, *args):
		pass # Super object function is overriden only if needed


	def onAuthenticated(self, session):
		pass # Super object function is overriden only if needed


	def onAuthenticationFailed(self, session):
		pass # Super object function is overriden only if needed


	def onAudioFrame(self, **kwargs):
		pass # Super object function is overriden only if needed


	def onSnipsAssistantInstalled(self, **kwargs):
		pass # Super object function is overriden only if needed


	def onSnipsAssistantFailedTraining(self, **kwargs):
		pass # Super object function is overriden only if needed


	def onSkillInstallFailed(self, skill: str):
		pass # Super object function is overriden only if needed


	def onNluTrained(self, **kwargs):
		pass # Super object function is overriden only if needed


	def onVadUp(self, **kwargs):
		pass # Super object function is overriden only if needed


	def onVadDown(self, **kwargs):
		pass # Super object function is overriden only if needed


	def onPlayBytes(self, requestId: str, payload: bytearray, siteId: str, sessionId: str = None):
		pass # Super object function is overriden only if needed


	def onPlayBytesFinished(self, requestId: str, siteId: str, sessionId: str = None):
		pass # Super object function is overriden only if needed


	def onToggleFeedbackOn(self, siteId: str):
		pass # Super object function is overriden only if needed


	def onToggleFeedbackOff(self, siteId: str):
		pass # Super object function is overriden only if needed


	def onPartialTextCaptured(self, session, text: str, likelihood: float, seconds: float):
		pass # Super object function is overriden only if needed


	def onEndSession(self, session, reason: str = 'nominal'):
		pass # Super object function is overriden only if needed


	def onDeviceHeartbeat(self, uid: str, siteId: str = None):
		pass # Super object function is overriden only if needed


	def onDeviceStatus(self, session):
		pass # Super object function is overriden only if needed


	def onSkillStarted(self, skill):
		"""
		param skill: AliceSkill instance
		"""
		pass  # Super object function is overriden only if needed


	def onSkillStopped(self, skill):
		"""
		:param skill: AliceSkill instance
		"""
		pass  # Super object function is overriden only if needed


	@property
	def ProjectAlice(self): #NOSONAR
		return SM.SuperManager.getInstance().projectAlice


	@property
	def ConfigManager(self): #NOSONAR
		return SM.SuperManager.getInstance().configManager


	@property
	def SkillManager(self): #NOSONAR
		return SM.SuperManager.getInstance().skillManager


	@property
	def DeviceManager(self): #NOSONAR
		return SM.SuperManager.getInstance().deviceManager


	@property
	def MultiIntentManager(self): #NOSONAR
		return SM.SuperManager.getInstance().multiIntentManager


	@property
	def ProtectedIntentManager(self): #NOSONAR
		return SM.SuperManager.getInstance().protectedIntentManager


	@property
	def MqttManager(self): #NOSONAR
		return SM.SuperManager.getInstance().mqttManager


	@property
	def UserManager(self): #NOSONAR
		return SM.SuperManager.getInstance().userManager


	@property
	def DatabaseManager(self): #NOSONAR
		return SM.SuperManager.getInstance().databaseManager


	@property
	def InternetManager(self): #NOSONAR
		return SM.SuperManager.getInstance().internetManager


	@property
	def TelemetryManager(self): #NOSONAR
		return SM.SuperManager.getInstance().telemetryManager


	@property
	def ThreadManager(self): #NOSONAR
		return SM.SuperManager.getInstance().threadManager


	@property
	def TimeManager(self): #NOSONAR
		return SM.SuperManager.getInstance().timeManager


	@property
	def ASRManager(self): #NOSONAR
		return SM.SuperManager.getInstance().asrManager


	@property
	def LanguageManager(self): #NOSONAR
		return SM.SuperManager.getInstance().languageManager


	@property
	def TalkManager(self): #NOSONAR
		return SM.SuperManager.getInstance().talkManager


	@property
	def TTSManager(self): #NOSONAR
		return SM.SuperManager.getInstance().ttsManager


	@property
	def WakewordRecorder(self): #NOSONAR
		return SM.SuperManager.getInstance().wakewordRecorder


	@property
	def WebInterfaceManager(self): #NOSONAR
		return SM.SuperManager.getInstance().webInterfaceManager


	@property
	def Commons(self): #NOSONAR
		return SM.SuperManager.getInstance().commonsManager


	@property
	def SkillStoreManager(self): #NOSONAR
		return SM.SuperManager.getInstance().skillStoreManager


	@property
	def NluManager(self): #NOSONAR
		return SM.SuperManager.getInstance().nluManager


	@property
	def DialogTemplateManager(self): #NOSONAR
		return SM.SuperManager.getInstance().dialogTemplateManager


	@property
	def AssistantManager(self): #NOSONAR
		return SM.SuperManager.getInstance().assistantManager


	@property
	def AliceWatchManager(self): #NOSONAR
		return SM.SuperManager.getInstance().aliceWatchManager


	@property
	def AudioServer(self): #NOSONAR
		return SM.SuperManager.getInstance().audioManager


	@property
	def DialogManager(self): #NOSONAR
		return SM.SuperManager.getInstance().dialogManager


	@property
	def LocationManager(self): #NOSONAR
		return SM.SuperManager.getInstance().locationManager


	@property
	def WakewordManager(self): #NOSONAR
		return SM.SuperManager.getInstance().wakewordManager
