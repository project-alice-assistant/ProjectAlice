from __future__ import annotations

import importlib
import inspect
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Union

import re
from copy import copy
from paho.mqtt import client as MQTTClient

from core.ProjectAliceExceptions import AccessLevelTooLow, SkillStartingFailed
from core.base.model import Widget
from core.base.model.Intent import Intent
from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.base.model.Version import Version
from core.commons import constants
from core.device.model.DeviceType import DeviceType
from core.dialog.model.DialogSession import DialogSession
from core.user.model.AccessLevels import AccessLevel


class AliceSkill(ProjectAliceObject):


	def __init__(self, supportedIntents: Iterable = None, databaseSchema: dict = None, **kwargs):
		super().__init__(**kwargs)
		try:
			self._skillPath = Path(inspect.getfile(self.__class__)).parent
			self._installFile = Path(inspect.getfile(self.__class__)).with_suffix('.install')
			self._installer = json.loads(self._installFile.read_text())
		except FileNotFoundError:
			raise SkillStartingFailed(skillName=constants.UNKNOWN, error=f'[{type(self).__name__}] Cannot find install file')
		except Exception as e:
			raise SkillStartingFailed(skillName=constants.UNKNOWN, error=f'[{type(self).__name__}] Failed loading skill: {e}')

		self._name = self._installer['name']
		self._author = self._installer['author']
		self._version = self._installer['version']
		self._icon = self._installer['icon']
		self._description = self._installer['desc']
		self._category = self._installer['category'] if 'category' in self._installer else 'undefined'
		self._conditions = self._installer['conditions']
		self._updateAvailable = False
		self._active = False
		self._delayed = False
		self._required = False
		self._databaseSchema = databaseSchema
		self._widgets = dict()
		self._deviceTypes = dict()
		self._intentsDefinitions = dict()
		self._scenarioNodeName = ''
		self._scenarioNodeVersion = Version(mainVersion=0, updateVersion=0, hotfix=0)

		self._supportedIntents: Dict[str, Intent] = self.buildIntentList(supportedIntents)
		self.loadIntentsDefinition()

		self._utteranceSlotCleaner = re.compile('{(.+?):=>.+?}')


	def addUtterance(self, text: str, intent: str) -> bool:
		file = self.getResource(f'dialogTemplate/{self.activeLanguage()}.json')
		if not file:
			return False

		data = json.loads(file.read_text())
		if 'intents' not in data:
			return False

		for i, declaredIntent in enumerate(data['intents']):
			if declaredIntent['name'].lower() != intent.lower():
				continue

			utterances = declaredIntent.get('utterances', list())
			if not text in utterances:
				utterances.append(text)
				data['intents'][i]['utterances'] = utterances
				file.write_text(json.dumps(data, ensure_ascii=False, indent=4))
				return True

		return False


	def loadScenarioNodes(self):
		path = self.getResource('scenarioNodes/package.json')
		if not path.exists():
			return

		try:
			with path.open('r') as fp:
				data = json.load(fp)
				self._scenarioNodeName = data['name']
				self._scenarioNodeVersion = Version.fromString(data['version'])
		except Exception as e:
			self.logWarning(f'Failed to load scenario nodes: {e}')


	def loadIntentsDefinition(self):
		dialogTemplate = self.getResource('dialogTemplate')

		for lang in self.LanguageManager.supportedLanguages:
			try:
				path = dialogTemplate / f'{lang}.json'
				if not path.exists():
					continue

				with path.open('r') as fp:
					data = json.load(fp)

					if 'intents' not in data:
						continue

					self._intentsDefinitions[lang] = dict()
					for intent in data['intents']:
						self._intentsDefinitions[lang][intent['name']] = intent['utterances']
			except Exception as e:
				self.logWarning(f'Something went wrong loading intent definition for skill **{self._name}**, language **{lang}**: {e}')


	def buildIntentList(self, supportedIntents) -> dict:
		supportedIntents = supportedIntents or list()
		intents: Dict[str, Intent] = self.findDecoratedIntents()
		for item in supportedIntents:
			if isinstance(item, tuple):
				intent = item[0]
				if not isinstance(intent, Intent):
					intent = Intent(intent, userIntent=False)

				intent.fallbackFunction = item[1]
				item = intent
			elif not isinstance(item, Intent):
				item = Intent(item, userIntent=False)

			if str(item) in intents:
				intents[str(item)].addDialogMapping(item.dialogMapping, skillName=self.name)

				if item.fallbackFunction:
					intents[str(item)].fallbackFunction = item.fallbackFunction

				# always use the highest auth level specified (low values mean a higher auth level)
				if item.authLevel < intents[str(item)].authLevel:
					intents[str(item)].authLevel = item.authLevel
			else:
				intents[str(item)] = item

		return intents


	def findDecoratedIntents(self) -> dict:
		intentMappings = dict()
		functionNames = [name for name, func in self.__class__.__dict__.items() if callable(func)]
		for name in functionNames:
			function = getattr(self, name)
			intents = getattr(function, 'intents', list())
			for intentMapping in intents:
				intent = intentMapping['intent']
				requiredState = intentMapping['requiredState']
				if str(intent) not in intentMappings:
					intentMappings[str(intent)] = intent

				if requiredState:
					intentMappings[str(intent)].addDialogMapping({requiredState: function}, skillName=self.name)
				else:
					intentMappings[str(intent)].fallbackFunction = function

				# always use the highest auth level specified (low values mean a higher auth level)
				if intent.authLevel < intentMappings[str(intent)].authLevel:
					intentMappings[str(intent)].authLevel = intent.authLevel

		return intentMappings


	# noinspection SqlResolve
	def loadWidgets(self):
		fp = self.getResource('widgets')
		if fp.exists():
			self.logInfo(f"Loading **{len(list(fp.glob('*.py'))) - 1}** widget", plural='widget')

			data = self.DatabaseManager.fetch(
				tableName='widgets',
				query='SELECT * FROM :__table__ WHERE parent = :parent ORDER BY `zindex`',
				callerName=self.SkillManager.name,
				values={'parent': self.name},
				method='all'
			)
			if data:
				data = {row['name']: row for row in data}

			for file in fp.glob('*.py'):
				if file.name.startswith('__'):
					continue

				widgetName = Path(file).stem
				widgetImport = importlib.import_module(f'skills.{self.name}.widgets.{widgetName}')
				klass = getattr(widgetImport, widgetName)

				if widgetName in data:  # widget already exists in DB
					widget = klass(data[widgetName])
					self._widgets[widgetName] = widget
					widget.setParentSkillInstance(self)
					del data[widgetName]
					self.logInfo(f'Loaded widget **{widgetName}**')

				else:  # widget is new
					self.logInfo(f'Adding widget **{widgetName}**')
					widget = klass({
						'name'  : widgetName,
						'parent': self.name,
					})
					self._widgets[widgetName] = widget
					widget.setParentSkillInstance(self)
					widget.saveToDB()

			for widgetName in data:  # deprecated widgets
				self.logInfo(f'Widget **{widgetName}** is deprecated, removing')
				self.DatabaseManager.delete(
					tableName='widgets',
					callerName=self.SkillManager.name,
					query='DELETE FROM :__table__ WHERE parent = :parent AND name = :name',
					values={
						'parent': self.name,
						'name'  : widgetName
					}
				)


	def loadDevices(self):
		fp = self.getResource('device')
		if fp.exists():
			self.logInfo(f"Loading **{len(list(fp.glob('*.py')))}** device type", plural='type')

			data = self.DeviceManager.getDeviceTypeBySkillRAW(skill=self.name)

			for file in fp.glob('*.py'):
				if file.name.startswith('__'):
					continue

				deviceType = Path(file).stem
				deviceTypeImport = importlib.import_module(f'skills.{self.name}.device.{deviceType}')
				klass = getattr(deviceTypeImport, deviceType)

				if deviceType in data:  # deviceType already exists in DB
					deviceClass = klass(data[deviceType])
					self._deviceTypes[deviceClass.id] = deviceClass
					del data[deviceType]
					self.logInfo(f'Loaded device type **{deviceType}**')
				else:  # deviceClass is new
					self.logInfo(f'Adding new device type **{deviceType}**')
					deviceClass = klass({'name': deviceType, 'skill': self.name})
					self._deviceTypes[deviceClass.id] = deviceClass

				deviceClass.parentSkillInstance = self
				deviceClass.onStart()

			for deviceType in data:  # deprecated devices
				self.logInfo(f'Device type **{deviceType}** is deprecated, removing')
				self.DeviceManager.removeDeviceTypeName(_name=deviceType)



	def getWidgetInstance(self, widgetName: str) -> Optional[Widget]:
		return self._widgets.get(widgetName)

	def getDeviceTypeInstance(self, deviceTypeName: str) -> Optional[DeviceType]:
		return self._deviceTypes.get(deviceTypeName)


	def getUtterancesByIntent(self, intent: Union[Intent, tuple, str], forceLowerCase: bool = True, cleanSlots: bool = False) -> list:
		lang = self.LanguageManager.activeLanguage
		if lang not in self._intentsDefinitions:
			return list()

		if isinstance(intent, tuple):
			check = intent[0].action
		elif isinstance(intent, Intent):
			check = intent.action
		else:
			check = str(intent).split('/')[-1].split(':')[-1]

		if check not in self._intentsDefinitions[lang]:
			return list()

		if not cleanSlots:
			return list(self._intentsDefinitions[lang][check])

		return [re.sub(self._utteranceSlotCleaner, '\\1', utterance.lower() if forceLowerCase else utterance)
			for utterance in self._intentsDefinitions[lang][check]]


	@property
	def widgets(self) -> dict:
		return self._widgets


	@property
	def deviceTypes(self) -> dict:
		return self._deviceTypes


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
	def description(self) -> str:
		return self._description


	@description.setter
	def description(self, value: str):
		self._description = value


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
	def delayed(self) -> bool:
		return self._delayed


	@delayed.setter
	def delayed(self, value: bool):
		self._delayed = value


	@property
	def scenarioNodeName(self) -> str:
		return self._scenarioNodeName


	@property
	def scenarioNodeVersion(self) -> Version:
		return self._scenarioNodeVersion


	@property
	def icon(self) -> str:
		return self._icon


	@property
	def installFile(self) -> Path:
		return self._installFile


	@property
	def skillPath(self) -> Path:
		return self._skillPath


	def hasScenarioNodes(self) -> bool:
		return self._scenarioNodeName != ''


	def subscribeIntents(self):
		self.MqttManager.subscribeSkillIntents(self._supportedIntents)


	def unsubscribeIntents(self):
		self.MqttManager.unsubscribeSkillIntents(self._supportedIntents)


	def notifyDevice(self, topic: str, uid: str = '', siteId: str = ''):
		if uid:
			self.MqttManager.publish(topic=topic, payload={'uid': uid})
		elif siteId:
			self.MqttManager.publish(topic=topic, payload={'siteId': siteId})
		else:
			self.logWarning('Tried to notify devices but no uid or site id specified')


	def authenticateIntent(self, session: DialogSession):
		intent = self._supportedIntents[session.message.topic]
		# Return if intent is for auth users only but the user is unknown
		if session.user == constants.UNKNOWN_USER:
			self.endDialog(
				sessionId=session.sessionId,
				text=self.TalkManager.randomTalk(talk='unknowUser', skill='system')
			)
			raise AccessLevelTooLow()
		# Return if intent is for auth users only and the user doesn't have the accesslevel for it
		if not self.UserManager.hasAccessLevel(session.user, intent.authLevel):
			self.endDialog(
				sessionId=session.sessionId,
				text=self.TalkManager.randomTalk(talk='noAccess', skill='system')
			)
			raise AccessLevelTooLow()


	@staticmethod
	def intentNameMoreSpecific(intentName: str, oldIntentName: str) -> bool:
		cleanedIntentName = intentName.rstrip('#').split('+')[0]
		cleanedOldIntentName = oldIntentName.rstrip('#').split('+')[0]
		return cleanedIntentName > cleanedOldIntentName


	def filterIntent(self, session: DialogSession) -> Optional[Intent]:
		# Return if the skill isn't active
		if not self.active:
			return None

		# search for intent that has a matching mqtt topic
		matchingIntent = None
		oldIntentName = None
		for intentName, intent in self._supportedIntents.items():
			if MQTTClient.topic_matches_sub(intentName, session.message.topic) and (not matchingIntent or self.intentNameMoreSpecific(intentName, oldIntentName)):
				matchingIntent = intent
				oldIntentName = intentName

		return matchingIntent


	def onMessageDispatch(self, session: DialogSession) -> bool:
		intent = self.filterIntent(session)
		if not intent:
			return False

		if intent.authLevel != AccessLevel.ZERO:
			try:
				self.authenticateIntent(session)
			except AccessLevelTooLow:
				raise

		function = intent.getMapping(session) or self.onMessage
		ret = function(session=session)
		return True if ret is None or ret == True else False


	def getResource(self, resourcePathFile: str = '') -> Path:
		return self.skillPath / resourcePathFile


	def _initDB(self) -> bool:
		if self._databaseSchema:
			return self.DatabaseManager.initDB(schema=self._databaseSchema, callerName=self.name)
		return True


	def onStart(self):
		self.logInfo(f'Starting')
		self._active = True

		self._initDB()
		self.SkillManager.configureSkillIntents(self._name, True)
		self.LanguageManager.loadSkillStrings(self.name)
		self.TalkManager.loadSkillTalks(self.name)

		self.loadWidgets()
		self.loadDevices()
		self.loadScenarioNodes()

		self.logInfo(f'![green](Started!)')


	def onStop(self):
		self._active = False
		self.SkillManager.configureSkillIntents(self._name, False)
		for devt in self.DeviceManager.getDeviceTypesForSkill(self.name).values():
			devt.onStop()
		self.logInfo(f'![green](Stopped)')
		self.broadcast(method=constants.EVENT_SKILL_STOPPED, exceptions=[self.name], propagateToSkills=True, skill=self)


	def onBooted(self) -> bool:
		if self.delayed:
			self.logInfo('Delayed start')
			self.ThreadManager.doLater(interval=5, func=self.onStart)

		return True


	def onSkillInstalled(self, **kwargs):
		self.onSkillUpdated(**kwargs)


	def onSkillUpdated(self, **kwargs):
		self._updateAvailable = False
		self.MqttManager.subscribeSkillIntents(self.name)


	def onSkillDeleted(self, skill: str):
		if skill != self.name or not self._databaseSchema:
			return

		for tableName in self._databaseSchema:
			self.DatabaseManager.dropTable(tableName=tableName, callerName=self.name)


	# HELPERS
	def getConfig(self, key: str) -> Any:
		return self.ConfigManager.getSkillConfigByName(skillName=self.name, configName=key)


	def getSkillConfigs(self) -> dict:
		ret = copy(self.ConfigManager.getSkillConfigs(self.name))
		ret.pop('active', None)
		return ret


	def getSkillConfigsTemplate(self) -> dict:
		return self.ConfigManager.getSkillConfigsTemplate(self.name)


	def updateConfig(self, key: str, value: Any):
		self.ConfigManager.updateSkillConfigurationFile(skillName=self.name, key=key, value=value)


	def getAliceConfig(self, key: str) -> Any:
		return self.ConfigManager.getAliceConfigByName(configName=key)


	def updateAliceConfig(self, key: str, value: Any):
		self.ConfigManager.updateAliceConfiguration(key=key, value=value)


	def activeLanguage(self) -> str:
		return self.LanguageManager.activeLanguage


	def defaultLanguage(self) -> str:
		return self.LanguageManager.defaultLanguage


	def databaseFetch(self, tableName: str, query: str, values: dict = None, method: str = 'one') -> sqlite3.Row:
		return self.DatabaseManager.fetch(tableName=tableName, query=query, values=values, callerName=self.name, method=method)


	def databaseInsert(self, tableName: str, query: str = None, values: dict = None) -> int:
		return self.DatabaseManager.insert(tableName=tableName, query=query, values=values, callerName=self.name)


	def randomTalk(self, text: str, replace: list = None, skill: str = None) -> str:
		talk = self.TalkManager.randomTalk(talk=text, skill=skill or self.name)

		if replace:
			talk = talk.format(*replace)
		return talk


	def getSkillInstance(self, skillName: str) -> AliceSkill:
		return self.SkillManager.getSkillInstance(skillName=skillName)


	def say(self, text: str, siteId: str = None, customData: dict = None, canBeEnqueued: bool = True):
		self.MqttManager.say(text=text, client=siteId, customData=customData, canBeEnqueued=canBeEnqueued)


	def ask(self, text: str, siteId: str = None, intentFilter: list = None, customData: dict = None, canBeEnqueued: bool = True, currentDialogState: str = '', probabilityThreshold: float = None):
		if currentDialogState:
			currentDialogState = f'{self.name}:{currentDialogState}'
		self.MqttManager.ask(text=text, client=siteId, intentFilter=intentFilter, customData=customData, canBeEnqueued=canBeEnqueued, currentDialogState=currentDialogState, probabilityThreshold=probabilityThreshold)


	def continueDialog(self, sessionId: str, text: str, customData: dict = None, intentFilter: list = None, slot: str = '', currentDialogState: str = '', probabilityThreshold: float = None):
		if currentDialogState:
			currentDialogState = f'{self.name}:{currentDialogState}'
		self.MqttManager.continueDialog(sessionId=sessionId, text=text, customData=customData, intentFilter=intentFilter, slot=slot, currentDialogState=currentDialogState, probabilityThreshold=probabilityThreshold)


	def endDialog(self, sessionId: str = '', text: str = '', siteId: str = ''):
		self.MqttManager.endDialog(sessionId=sessionId, text=text, client=siteId)


	def endSession(self, sessionId):
		self.MqttManager.endSession(sessionId=sessionId)


	def playSound(self, soundFilename: str, location: Path = None, sessionId: str = '', siteId: str = None, uid: str = ''):
		self.MqttManager.playSound(soundFilename=soundFilename, location=location, sessionId=sessionId, siteId=siteId, uid=uid)


	def publish(self, topic: str, payload: dict = None, stringPayload: str = None, qos: int = 0, retain: bool = False):
		self.MqttManager.publish(topic=topic, payload=payload, stringPayload=stringPayload, qos=qos, retain=retain)


	def __repr__(self) -> str:
		return json.dumps(self.toJson())


	def __str__(self) -> str:
		return self.__repr__()


	def toJson(self) -> dict:
		return {
			'name'           : self._name,
			'author'         : self._author,
			'version'        : self._version,
			'updateAvailable': self._updateAvailable,
			'active'         : self._active,
			'delayed'        : self._delayed,
			'required'       : self._required,
			'databaseSchema' : self._databaseSchema
		}
