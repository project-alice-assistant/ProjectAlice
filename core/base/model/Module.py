# -*- coding: utf-8 -*-
import inspect
import json
import logging
import typing

from pathlib import Path

from paho.mqtt import client as MQTTClient

from core.commons import commons
import core.base.Managers as managers
from core.dialog.model.DialogSession import DialogSession
from core.ProjectAliceExceptions import ModuleStartingFailed, AccessLevelTooLow
from core.base.model.Intent import Intent


class Module(object):

	def __init__(self, supportedIntents: list, authOnlyIntents: dict = None, databaseSchema: dict = None):
		self._logger = logging.getLogger('ProjectAlice')

		try:
			path = Path(inspect.getfile(self.__class__)).with_suffix('.install')
			self._install = json.load(path.read_text())
		except FileNotFoundError:
			raise ModuleStartingFailed(error = '[{}] Cannot find install file'.format(type(self).__name__))
		except Exception as e:
			raise ModuleStartingFailed(error = '[{}] Failed loading module: {}'.format(type(self).__name__, e))

		self._name = self._install['name']
		self._delayed = False
		self._databaseSchema = databaseSchema

		self._supportedIntents = supportedIntents
		self._authOnlyIntents = authOnlyIntents or dict()


	def getUtterancesByIntent(self, intent: Intent, forceLowerCase: bool = True) -> list:
		utterances = list()

		for dtIntentName, dtModuleName in managers.SamkillaManager.dtIntentNameSkillMatching.items():
			if dtIntentName == intent.justAction and dtModuleName == self.name:

				for utterance in managers.SamkillaManager.dtIntentsModulesValues[dtIntentName]['utterances']:
					utterances.append(utterance.lower() if forceLowerCase else utterance)

		return utterances


	def getCurrentDir(self):
		return Path(inspect.getfile(self.__class__)).parent


	@property
	def name(self) -> str:
		return self._name


	@name.setter
	def name(self, value: str):
		self._name = value


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


	def onStart(self) -> list:
		self._logger.info('Starting {} module'.format(self.name))
		self._initDB()
		return self._supportedIntents


	def subscribe(self, mqttClient: MQTTClient):
		for intent in self._supportedIntents:
			mqttClient.subscribe(str(intent))


	@staticmethod
	def broadcast(topic: str):
		managers.MqttServer.publish(topic = topic)


	def notifyDevice(self, topic: str, uid: str = '', siteId: str = ''):
		if uid:
			managers.MqttServer.publish(topic = topic, payload = {'uid': uid})
		elif siteId:
			managers.MqttServer.publish(topic = topic, payload = {'siteId': siteId})
		else:
			self._logger.warning('[{}] Tried to notify devices but no uid or site id specified'.format(self.name))


	def filterIntent(self, intent: str, session: DialogSession) -> bool:
		# Return if previous intent is not supported by this module
		if session.previousIntent and session.previousIntent not in self._supportedIntents:
			return False

		# Return if this intent is not supported by this module
		if not intent in self._supportedIntents:
			return False

		if intent in self._authOnlyIntents:
			# Return if intent is for auth users only but the user is unknown
			if session.user == 'unknown':
				managers.MqttServer.endTalk(
					sessionId=session.sessionId,
					text=managers.TalkManager.randomTalk(talk='unknowUser', module='system')
				)
				raise AccessLevelTooLow()
			# Return if intent is for auth users only and the user doesn't have the accesslevel for it
			if not managers.UserManager.hasAccessLevel(session.user, self._authOnlyIntents[intent]):
				managers.MqttServer.endTalk(
					sessionId=session.sessionId,
					text=managers.TalkManager.randomTalk(talk='noAccess', module='system')
				)
				raise AccessLevelTooLow()

		return True


	def getResource(self, moduleName: str = '', resourcePathFile: str = '') -> str:
		return commons.rootDir() / 'modules' / moduleName or self.name, resourcePathFile


	def getConfig(self, key: str) -> typing.Any:
		return managers.ConfigManager.getModuleConfigByName(moduleName=self.name, configName=key)


	def updateConfig(self, key: str, value: typing.Any) -> typing.Any:
		managers.ConfigManager.updateModuleConfigurationFile(moduleName=self.name, key=key, value=value)


	@staticmethod
	def getAliceConfig(key: str) -> typing.Any:
		return managers.ConfigManager.getAliceConfigByName(configName=key)


	@staticmethod
	def updateAliceConfig(key: str, value: typing.Any) -> typing.Any:
		managers.ConfigManager.updateAliceConfiguration(key=key, value=value)


	@staticmethod
	def activeLanguage() -> str:
		return managers.LanguageManager.activeLanguage


	@staticmethod
	def defaultLanguage() -> str:
		return managers.LanguageManager.defaultLanguage


	def _initDB(self) -> bool:
		if self._databaseSchema:
			return managers.DatabaseManager.initDB(schema=self._databaseSchema, callerName=self.name)
		return True


	def databaseFetch(self, tableName: str, query: str, values: dict = None, method: str = 'one') -> list:
		return managers.DatabaseManager.fetch(tableName=tableName, query=query, values=values, callerName=self.name, method=method)


	def databaseInsert(self, tableName: str, query: str, values: dict = None) -> int:
		return managers.DatabaseManager.insert(tableName=tableName, query=query, values=values, callerName=self.name)


	def randomTalk(self, text: str, replace: list = None) -> str:
		string = managers.TalkManager.randomTalk(talk=text, module=self.name)

		if replace:
			string = string.format(*replace)

		return string


	@staticmethod
	def getModuleInstance(moduleName: str):
		return managers.ModuleManager.getModuleInstance(moduleName=moduleName)


	@staticmethod
	def say(text: str, siteId: str = 'default', customData: dict = None, canBeEnqueued: bool = True):
		managers.MqttServer.say(text=text, client=siteId, customData=customData, canBeEnqueued=canBeEnqueued)


	@staticmethod
	def ask(text: str, siteId: str = 'default', intentFilter: list = None, customData: dict = None, previousIntent: str = '', canBeEnqueued: bool = True):
		managers.MqttServer.ask(text=text, client=siteId, intentFilter=intentFilter, customData=customData, previousIntent=previousIntent, canBeEnqueued=canBeEnqueued)


	@staticmethod
	def continueDialog(sessionId: str, text: str, customData: dict = None, intentFilter: list = None, previousIntent: typing.Any = None, slot: str = ''):
		managers.MqttServer.continueDialog(sessionId=sessionId, text=text, customData=customData, intentFilter=intentFilter, previousIntent=str(previousIntent), slot=slot)


	@staticmethod
	def endDialog(sessionId: str = '', text: str = '', siteId: str = ''):
		managers.MqttServer.endTalk(sessionId=sessionId, text=text, client=siteId)


	@staticmethod
	def endSession(sessionId):
		managers.MqttServer.endSession(sessionId=sessionId)


	@staticmethod
	def playSound(soundFile: str, sessionId: str = '', absolutePath: bool = False, siteId: str = 'default', root: str = '', uid: str = ''):
		managers.MqttServer.playSound(soundFile=soundFile, sessionId=sessionId, absolutePath=absolutePath, siteId=siteId, root=root, uid=uid)


	@staticmethod
	def publish(topic: str, payload: dict = None, qos: int = 0, retain: bool = False):
		managers.MqttServer.publish(topic=topic, payload=payload, qos=qos, retain=retain)


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

	def onBooted(self):
		if self.delayed:
			self._logger.info('[{}] Delayed start'.format(self.name))
			if managers.ThreadManager.getLock('SnipsAssistantDownload').isSet():
				managers.ThreadManager.doLater(interval=5, func=self.onBooted)
				return False
			else:
				managers.ThreadManager.doLater(interval=5, func=self.onStart)

		return True

	def onModuleInstalled(self):
		managers.MqttServer.subscribeModuleIntents(self.name)

	def onModuleUpdated(self):
		managers.MqttServer.subscribeModuleIntents(self.name)

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
