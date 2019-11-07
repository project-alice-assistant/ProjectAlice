from __future__ import annotations

import importlib
import inspect
import json
import sqlite3
import functools

import re

from typing import Dict, Iterable, Callable, Any, Tuple, List, Generator
from pathlib import Path

from paho.mqtt import client as MQTTClient

from core.ProjectAliceExceptions import AccessLevelTooLow, ModuleStartingFailed
from core.base.model.Intent import Intent
from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.user.model.AccessLevels import AccessLevel
from core.util.Decorators import IntentHandler


class Module(ProjectAliceObject):

	def __init__(self, supportedIntents: Iterable = None, authOnlyIntents: dict = None, databaseSchema: dict = None):
		super().__init__(logDepth=4)
		try:
			path = Path(inspect.getfile(self.__class__)).with_suffix('.install')
			self._install = json.loads(path.read_text())
		except FileNotFoundError:
			raise ModuleStartingFailed(error=f'[{type(self).__name__}] Cannot find install file')
		except Exception as e:
			raise ModuleStartingFailed(error=f'[{type(self).__name__}] Failed loading module: {e}')

		self._name = self._install['name']
		self._author = self._install['author']
		self._version = self._install['version']
		self._updateAvailable = False
		self._active = True
		self._delayed = False
		self._required = False
		self._databaseSchema = databaseSchema
		self._widgets = dict()

		if not supportedIntents:
			supportedIntents = list()

		self._myIntents: List[Intent] = list()
		self._supportedIntents: Dict[str, Tuple[(str, Intent), Callable]] = dict()
		for item in (*supportedIntents, *self.intentMethods()):
			if isinstance(item, tuple):
				self._supportedIntents[str(item[0])] = item
				self._myIntents.append(item[0])
			elif isinstance(item, Intent):
				self._supportedIntents[str(item)] = (item, self.onMessage)
				self._myIntents.append(item)
			elif isinstance(item, str):
				self._supportedIntents[item] = (item, self.onMessage)

		self._authOnlyIntents: Dict[str, AccessLevel] = {str(intent): level.value for intent, level in authOnlyIntents.items()} if authOnlyIntents else dict()
		self._utteranceSlotCleaner = re.compile('{(.+?):=>.+?}')
		self.loadWidgets()


	@classmethod
	def decoratedIntentMethods(cls) -> Generator[IntentHandler.Wrapper, None, None]:
		for name in dir(cls):
			method = getattr(cls, name)
			while isinstance(method, IntentHandler.Wrapper):
				yield method
				method = method.decoratedMethod


	@classmethod
	def intentMethods(cls) -> list:
		intents = dict()
		for method in cls.decoratedIntentMethods():
			if not method.requiredState:
				intents[method.intentName] = (method.intent, method)
				continue

			if method.intentName not in intents:
				intents[method.intentName] = method.intent

			intents[method.intentName].addDialogMapping({method.requiredState: method})

		return list(intents.values())


	# noinspection SqlResolve
	def loadWidgets(self):
		fp = Path(self.getCurrentDir(), 'widgets')
		if fp.exists():
			self.logInfo(f"Loading {len(list(fp.glob('*.py'))) - 1} widgets")

			data = self.DatabaseManager.fetch(
				tableName='widgets',
				query='SELECT * FROM :__table__ WHERE parent = :parent ORDER BY `zindex`',
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
				widgetImport = importlib.import_module(f'modules.{self.name}.widgets.{widgetName}')
				klass = getattr(widgetImport, widgetName)

				if widgetName in data: # widget already exists in DB
					self._widgets[widgetName] = klass(data[widgetName])
					del data[widgetName]
					self.logInfo(f'Loaded widget "{widgetName}"')

				else: # widget is new
					self.logInfo(f'Adding widget "{widgetName}"')
					widget = klass({
						'name': widgetName,
						'parent': self.name,
					})
					self._widgets[widgetName] = widget
					widget.saveToDB()

			for widgetName in data: # deprecated widgets
				self.logInfo(f'Widget "{widgetName}" is deprecated, removing')
				self.DatabaseManager.delete(
					tableName='widgets',
					callerName=self.ModuleManager.name,
					query='DELETE FROM :__table__ WHERE parent = :parent AND name = :name',
					values={
						'parent': self.name,
						'name': widgetName
					}
				)


	def getUtterancesByIntent(self, intent: Intent, forceLowerCase: bool = True, cleanSlots: bool = False) -> list:
		utterances = list()

		if isinstance(intent, tuple):
			check = intent[0].justAction
		elif isinstance(intent, Intent):
			check = intent.justAction
		else:
			check = intent.split('/')[-1].split(':')[-1]

		for dtIntentName, dtModuleName in self.SamkillaManager.dtIntentNameSkillMatching.items():
			if dtIntentName == check and dtModuleName == self.name:

				for utterance in self.SamkillaManager.dtIntentsModulesValues[dtIntentName]['utterances']:
					if cleanSlots:
						utterance = re.sub(self._utteranceSlotCleaner, '\\1', utterance)

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
	def supportedIntents(self) -> dict:
		return self._supportedIntents


	@supportedIntents.setter
	def supportedIntents(self, value: list):
		self._supportedIntents = value


	@property
	def myIntents(self) -> list:
		return self._myIntents


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
				self.logError(f'Failed subscribing to intent "{str(intent)}"')


	def notifyDevice(self, topic: str, uid: str = '', siteId: str = ''):
		if uid:
			self.MqttManager.publish(topic=topic, payload={'uid': uid})
		elif siteId:
			self.MqttManager.publish(topic=topic, payload={'siteId': siteId})
		else:
			self.logWarning('Tried to notify devices but no uid or site id specified')


	def filterIntent(self, intent: str, session: DialogSession) -> bool:
		# Return if the module isn't active
		if not self.active:
			return False

		# Return if previous intent is not supported by this module
		if session.previousIntent and str(session.previousIntent) not in self._supportedIntents:
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


	def dispatchMessage(self, intent: str, session: DialogSession) -> bool:
		forMe = self.filterIntent(intent, session)
		if not forMe:
			return False

		intentt = self._supportedIntents[intent][0]
		if isinstance(intentt, Intent) and intentt.hasDialogMapping():
			consumed = self._supportedIntents[intent][0].dialogMapping.onDialog(intent, session, self.name)
			if consumed or consumed is None:
				return True

		return self._supportedIntents[intent][1](session=session, intent=intent)


	def getResource(self, moduleName: str = '', resourcePathFile: str = '') -> str:
		return str(Path(self.Commons.rootDir(), 'modules', moduleName or self.name, resourcePathFile))


	def _initDB(self) -> bool:
		if self._databaseSchema:
			return self.DatabaseManager.initDB(schema=self._databaseSchema, callerName=self.name)
		return True


	def onStart(self) -> dict:
		if not self._active:
			self.logInfo(f'Module {self.name} is not active')
		else:
			self.logInfo(f'Starting {self.name} module')

		self._initDB()
		self.MqttManager.subscribeModuleIntents(self.name)
		return self._supportedIntents


	def onBooted(self):
		if self.delayed:
			if self.ThreadManager.getEvent('SnipsAssistantDownload').isSet():
				self.ThreadManager.doLater(interval=5, func=self.onBooted)
				return False

			self.logInfo('Delayed start')
			self.ThreadManager.doLater(interval=5, func=self.onStart)

		return True


	def onModuleInstalled(self):
		self._updateAvailable = False
		#self.MqttManager.subscribeModuleIntents(self.name)


	def onModuleUpdated(self):
		self._updateAvailable = False
		#self.MqttManager.subscribeModuleIntents(self.name)


	# HELPERS
	def getConfig(self, key: str) -> Any:
		return self.ConfigManager.getModuleConfigByName(moduleName=self.name, configName=key)


	def getModuleConfigs(self, withInfo: bool = False) -> dict:
		if withInfo:
			return self.ConfigManager.getModuleConfigs(self.name)
		else:
			mySettings = self.ConfigManager.getModuleConfigs(self.name)
			infoSettings = self.ConfigManager.aliceModuleConfigurationKeys
			return {key: value for key, value in mySettings.items() if key not in infoSettings}


	def updateConfig(self, key: str, value: Any) -> Any:
		self.ConfigManager.updateModuleConfigurationFile(moduleName=self.name, key=key, value=value)


	def getAliceConfig(self, key: str) -> Any:
		return self.ConfigManager.getAliceConfigByName(configName=key)


	def updateAliceConfig(self, key: str, value: Any) -> Any:
		self.ConfigManager.updateAliceConfiguration(key=key, value=value)


	def activeLanguage(self) -> str:
		return self.LanguageManager.activeLanguage


	def defaultLanguage(self) -> str:
		return self.LanguageManager.defaultLanguage


	def databaseFetch(self, tableName: str, query: str, values: dict = None, method: str = 'one') -> sqlite3.Row:
		return self.DatabaseManager.fetch(tableName=tableName, query=query, values=values, callerName=self.name, method=method)


	def databaseInsert(self, tableName: str, query: str = None, values: dict = None) -> int:
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


	def ask(self, text: str, siteId: str = constants.DEFAULT_SITE_ID, intentFilter: list = None, customData: dict = None, previousIntent: str = '', canBeEnqueued: bool = True, currentDialogState: str = ''):
		self.MqttManager.ask(text=text, client=siteId, intentFilter=intentFilter, customData=customData, previousIntent=previousIntent, canBeEnqueued=canBeEnqueued, currentDialogState=currentDialogState)


	def continueDialog(self, sessionId: str, text: str, customData: dict = None, intentFilter: list = None, previousIntent: str = '', slot: str = '', currentDialogState: str = ''):
		self.MqttManager.continueDialog(sessionId=sessionId, text=text, customData=customData, intentFilter=intentFilter, previousIntent=str(previousIntent), slot=slot, currentDialogState=currentDialogState)


	def endDialog(self, sessionId: str = '', text: str = '', siteId: str = ''):
		self.MqttManager.endDialog(sessionId=sessionId, text=text, client=siteId)


	def endSession(self, sessionId):
		self.MqttManager.endSession(sessionId=sessionId)


	def playSound(self, soundFilename: str, location: Path = None, sessionId: str = '', siteId: str = constants.DEFAULT_SITE_ID, uid: str = ''):
		self.MqttManager.playSound(soundFilename=soundFilename, location=location, sessionId=sessionId, siteId=siteId, uid=uid)


	def publish(self, topic: str, payload: dict = None, qos: int = 0, retain: bool = False):
		self.MqttManager.publish(topic=topic, payload=payload, qos=qos, retain=retain)
