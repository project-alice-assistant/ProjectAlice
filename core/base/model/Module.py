from __future__ import annotations

import importlib
import inspect
import json
import logging
import typing
from pathlib import Path

from paho.mqtt import client as MQTTClient

from core.ProjectAliceExceptions import AccessLevelTooLow, ModuleStartingFailed
from core.base.SuperManager import SuperManager
from core.base.model.Intent import Intent
from core.commons import commons, constants
from core.dialog.model.DialogSession import DialogSession


class Module:

	def __init__(self, supportedIntents: list, authOnlyIntents: dict = None, databaseSchema: dict = None):
		self._logger = logging.getLogger('ProjectAlice')

		try:
			path = Path(inspect.getfile(self.__class__)).with_suffix('.install')
			self._install = json.loads(path.read_text())
		except FileNotFoundError:
			raise ModuleStartingFailed(error='[{}] Cannot find install file'.format(type(self).__name__))
		except Exception as e:
			raise ModuleStartingFailed(error='[{}] Failed loading module: {}'.format(type(self).__name__, e))

		self._name = self._install['name']
		self._author = self._install['author']
		self._version = self._install['version']
		self._updateAvailable = False
		self._active = True
		self._delayed = False
		self._required = False
		self._databaseSchema = databaseSchema
		self._widgets = dict()

		self._supportedIntents = supportedIntents
		self._authOnlyIntents = authOnlyIntents or dict()

		self.loadWidgets()


	def loadWidgets(self):
		fp = Path(self.getCurrentDir(), 'widgets')
		if fp.exists():
			self._logger.info('[{}] Loading {} widgets'.format(self.name, len(list(fp.glob('*.py'))) - 1))

			data = self.DatabaseManager.fetch(
				tableName='widgets',
				query='SELECT * FROM :__table__ WHERE parent = :parent',
				callerName=self.ModuleManager.name,
				values={'parent': self.name},
				method='all'
			)
			if data:
				data = {row['name']: row for row in data}

			for file in fp.glob('*.py'):
				if file.name.startswith('__'):
					continue

				widgetName = Path(file).stem
				widgetImport = importlib.import_module('modules.{}.widgets.{}'.format(self.name, widgetName))
				klass = getattr(widgetImport, widgetName)

				if widgetName in data: # widget already exists in DB
					self._widgets[widgetName] = klass(data[widgetName])
					del data[widgetName]
					self._logger.info('[{}] Loaded widget "{}"'.format(self.name, widgetName))

				else: # widget is new
					self._logger.info('[{}] Adding widget "{}"'.format(self.name, widgetName))
					widget = klass({
						'name': widgetName,
						'parent': self.name,
					})
					self._widgets[widgetName] = widget
					widget.saveToDB()

			for widgetName in data: # deprecated widgets
				self._logger.info('[{}] Widget "{}" is deprecated, removing'.format(self.name, widgetName))
				self.DatabaseManager.delete(
					tableName='widgets',
					callerName=self.ModuleManager.name,
					query='DELETE FROM :__table__ WHERE parent = :parent AND name = :name',
					values={
						'parent': self.name,
						'name': widgetName
					}
				)


	def getUtterancesByIntent(self, intent: Intent, forceLowerCase: bool = True) -> list:
		utterances = list()

		for dtIntentName, dtModuleName in SuperManager.getInstance().samkillaManager.dtIntentNameSkillMatching.items():
			if dtIntentName == intent.justAction and dtModuleName == self.name:

				for utterance in self.SamkillaManager.dtIntentsModulesValues[dtIntentName]['utterances']:
					utterances.append(utterance.lower() if forceLowerCase else utterance)

		return utterances


	def getCurrentDir(self):
		return Path(inspect.getfile(self.__class__)).parent


	@property
	def widgets(self) -> dict:
		return self._widgets


	@property
	def active(self) -> bool:
		return self._active


	@active.setter
	def active(self, value: bool):
		self._active = value


	@property
	def name(self) -> str:
		return self._name


	@name.setter
	def name(self, value: str):
		self._name = value


	@property
	def author(self) -> str:
		return self._author


	@author.setter
	def author(self, value: str):
		self._author = value


	@property
	def version(self) -> float:
		return self._version


	@version.setter
	def version(self, value: float):
		self._version = value


	@property
	def updateAvailable(self) -> bool:
		return self._updateAvailable


	@updateAvailable.setter
	def updateAvailable(self, value: bool):
		self._updateAvailable = value


	@property
	def required(self) -> bool:
		return self._required


	@required.setter
	def required(self, value: bool):
		self._required = value


	@property
	def supportedIntents(self) -> list:
		return self._supportedIntents


	@supportedIntents.setter
	def supportedIntents(self, value: list):
		self._supportedIntents = value


	@property
	def delayed(self) -> bool:
		return self._delayed


	@delayed.setter
	def delayed(self, value: bool):
		self._delayed = value


	def subscribe(self, mqttClient: MQTTClient):
		for intent in self._supportedIntents:
			try:
				mqttClient.subscribe(str(intent))
			except:
				self._logger.error('Failed subscribing to intent "{}"'.format(str(intent)))


	def notifyDevice(self, topic: str, uid: str = '', siteId: str = ''):
		if uid:
			self.MqttManager.publish(topic=topic, payload={'uid': uid})
		elif siteId:
			self.MqttManager.publish(topic=topic, payload={'siteId': siteId})
		else:
			self._logger.warning('[{}] Tried to notify devices but no uid or site id specified'.format(self.name))


	def filterIntent(self, intent: str, session: DialogSession) -> bool:
		# Return if the module isn't active
		if not self.active:
			return False

		# Return if previous intent is not supported by this module
		if session.previousIntent and session.previousIntent not in self._supportedIntents:
			return False

		# Return if this intent is not supported by this module
		if not intent in self._supportedIntents:
			return False

		if intent in self._authOnlyIntents:
			# Return if intent is for auth users only but the user is unknown
			if session.user == constants.UNKNOWN_USER:
				self.endDialog(
					sessionId=session.sessionId,
					text=self.TalkManager.randomTalk(talk='unknowUser', module='system')
				)
				raise AccessLevelTooLow()
			# Return if intent is for auth users only and the user doesn't have the accesslevel for it
			if not self.UserManager.hasAccessLevel(session.user, self._authOnlyIntents[intent]):
				self.endDialog(
					sessionId=session.sessionId,
					text=self.TalkManager.randomTalk(talk='noAccess', module='system')
				)
				raise AccessLevelTooLow()

		return True


	def getResource(self, moduleName: str = '', resourcePathFile: str = '') -> str:
		return str(Path(commons.rootDir(), 'modules', moduleName or self.name, resourcePathFile))


	def _initDB(self) -> bool:
		if self._databaseSchema:
			return self.DatabaseManager.initDB(schema=self._databaseSchema, callerName=self.name)
		return True


	def onHotword(self, siteId: str): pass
	def onSay(self, session: DialogSession): pass
	def onSayFinished(self, session: DialogSession): pass
	def onHotwordToggleOn(self, siteId: str): pass
	def onUserCancel(self, session: DialogSession): pass
	def onSessionTimeout(self, session: DialogSession): pass
	def onSessionError(self, session: DialogSession): pass
	def onSessionEnded(self, session: DialogSession): pass
	def onSessionStarted(self, session: DialogSession): pass
	def onSessionQueued(self, session: DialogSession): pass
	def onIntentNotRecognized(self, session: DialogSession): pass
	def onStartListening(self, session: DialogSession): pass
	def onCaptured(self, session: DialogSession): pass
	def onIntentParsed(self, session: DialogSession): pass


	def onStart(self) -> list:
		if not self._active:
			self._logger.info('Module {} is not active'.format(self.name))
		else:
			self._logger.info('Starting {} module'.format(self.name))

		self._initDB()
		self.MqttManager.subscribeModuleIntents(self.name)
		return self._supportedIntents


	def onBooted(self):
		if self.delayed:
			if self.ThreadManager.getLock('SnipsAssistantDownload').isSet():
				self.ThreadManager.doLater(interval=5, func=self.onBooted)
				return False

			self._logger.info('[{}] Delayed start'.format(self.name))
			self.ThreadManager.doLater(interval=5, func=self.onStart)

		return True

	def onModuleInstalled(self):
		self._updateAvailable = False
		self.MqttManager.subscribeModuleIntents(self.name)

	def onModuleUpdated(self):
		self._updateAvailable = False
		self.MqttManager.subscribeModuleIntents(self.name)

	def onSleep(self): pass
	def onWakeup(self): pass
	def onGoingBed(self): pass
	def onLeavingHome(self): pass
	def onReturningHome(self): pass
	def onEating(self): pass
	def onWatchingTV(self): pass
	def onCooking(self): pass
	def onMakeup(self): pass
	def onContextSensitiveDelete(self, sessionId: str):	pass
	def onContextSensitiveEdit(self, sessionId: str): pass
	def onStop(self): self._logger.info('[{}] Stopping'.format(self.name))
	def onFullMinute(self): pass
	def onFiveMinute(self): pass
	def onQuarterHour(self): pass
	def onFullHour(self): pass
	def onMessage(self, intent: str, session: DialogSession): raise NotImplementedError('[{}] onMessage must be implemented!'.format(self.name))
	def onCancel(self): pass
	def onASRCaptured(self, *args): pass
	def onWakeword(self): pass
	def onMotionDetected(self, *args): pass
	def onMotionStopped(self, *args): pass
	def onButtonPressed(self, *args): pass
	def onButtonReleased(self, *args): pass
	def onDeviceConnecting(self, *args): pass
	def onDeviceDisconnecting(self, *args): pass
	def onRaining(self, *args): pass
	def onWindy(self, *args): pass
	def onFreezing(self, deviceList: list): pass
	def onTemperatureAlert(self, deviceList: list): pass
	def onCO2Alert(self, deviceList: list): pass
	def onHumidityAlert(self, deviceList: list): pass
	def onNoiseAlert(self, deviceList: list): pass
	def onPressureAlert(self, deviceList: list): pass
	def onBroadcastingForNewDeviceStart(self, session: DialogSession): pass
	def onBroadcastingForNewDeviceStop(self, *args): pass
	def onSnipsAssistantDownloaded(self, *args): pass
	def onSnipsAssistantDownloadFailed(self, *args): pass
	def onAuthenticated(self, session: DialogSession, *args): pass
	def onAuthenticationFailed(self, session: DialogSession, *args): pass


	# HELPERS
	def getConfig(self, key: str) -> typing.Any:
		return self.ConfigManager.getModuleConfigByName(moduleName=self.name, configName=key)


	def updateConfig(self, key: str, value: typing.Any) -> typing.Any:
		self.ConfigManager.updateModuleConfigurationFile(moduleName=self.name, key=key, value=value)


	def getAliceConfig(self, key: str) -> typing.Any:
		return self.ConfigManager.getAliceConfigByName(configName=key)


	def updateAliceConfig(self, key: str, value: typing.Any) -> typing.Any:
		self.ConfigManager.updateAliceConfiguration(key=key, value=value)


	def activeLanguage(self) -> str:
		return self.LanguageManager.activeLanguage


	def defaultLanguage(self) -> str:
		return self.LanguageManager.defaultLanguage


	def databaseFetch(self, tableName: str, query: str, values: dict = None, method: str = 'one') -> list:
		return self.DatabaseManager.fetch(tableName=tableName, query=query, values=values, callerName=self.name, method=method)


	def databaseInsert(self, tableName: str, query: str, values: dict = None) -> int:
		return self.DatabaseManager.insert(tableName=tableName, query=query, values=values, callerName=self.name)


	def randomTalk(self, text: str, replace: list = None) -> str:
		string = self.TalkManager.randomTalk(talk=text, module=self.name)

		if replace:
			string = string.format(*replace)

		return string


	def getModuleInstance(self, moduleName: str) -> Module:
		return self.ModuleManager.getModuleInstance(moduleName=moduleName)


	def say(self, text: str, siteId: str = constants.DEFAULT_SITE_ID, customData: dict = None, canBeEnqueued: bool = True):
		self.MqttManager.say(text=text, client=siteId, customData=customData, canBeEnqueued=canBeEnqueued)


	def ask(self, text: str, siteId: str = constants.DEFAULT_SITE_ID, intentFilter: list = None, customData: dict = None, previousIntent: str = '', canBeEnqueued: bool = True):
		self.MqttManager.ask(text=text, client=siteId, intentFilter=intentFilter, customData=customData, previousIntent=previousIntent, canBeEnqueued=canBeEnqueued)


	def continueDialog(self, sessionId: str, text: str, customData: dict = None, intentFilter: list = None, previousIntent: str = '', slot: str = ''):
		self.MqttManager.continueDialog(sessionId=sessionId, text=text, customData=customData, intentFilter=intentFilter, previousIntent=str(previousIntent), slot=slot)


	def endDialog(self, sessionId: str = '', text: str = '', siteId: str = ''):
		self.MqttManager.endDialog(sessionId=sessionId, text=text, client=siteId)


	def endSession(self, sessionId):
		self.MqttManager.endSession(sessionId=sessionId)


	def playSound(self, soundFile: str, sessionId: str = '', absolutePath: bool = False, siteId: str = constants.DEFAULT_SITE_ID, root: str = '', uid: str = ''):
		self.MqttManager.playSound(soundFile=soundFile, sessionId=sessionId, absolutePath=absolutePath, siteId=siteId, root=root, uid=uid)


	def publish(self, topic: str, payload: dict = None, qos: int = 0, retain: bool = False):
		self.MqttManager.publish(topic=topic, payload=payload, qos=qos, retain=retain)


	def broadcast(self, topic: str):
		self.MqttManager.publish(topic=topic)


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
