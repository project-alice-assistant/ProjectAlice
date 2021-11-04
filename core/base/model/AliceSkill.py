#  Copyright (c) 2021
#
#  This file, AliceSkill.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.08.02 at 06:11:36 CEST

from __future__ import annotations

import importlib
import inspect
import json
import re
from copy import copy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

import flask
from markdown import markdown
from paho.mqtt import client as MQTTClient

from core.ProjectAliceExceptions import AccessLevelTooLow, SkillStartingFailed
from core.base.model.Intent import Intent
from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.base.model.Version import Version
from core.commons import constants
from core.device.model.Device import Device
from core.dialog.model.DialogSession import DialogSession
from core.user.model.AccessLevels import AccessLevel


class AliceSkill(ProjectAliceObject):

	def __init__(self, supportedIntents: Iterable = None, databaseSchema: dict = None, isNew: bool = False, **kwargs):
		super().__init__(**kwargs)

		if isNew:
			return

		try:
			self._skillPath = Path(inspect.getfile(self.__class__)).parent
			self._installFile = Path(inspect.getfile(self.__class__)).with_suffix('.install')
			self._installer = json.loads(self._installFile.read_text())
		except FileNotFoundError:
			raise SkillStartingFailed(skillName=constants.UNKNOWN, error=f'[{type(self).__name__}] Cannot find install file')
		except Exception as e:
			raise SkillStartingFailed(skillName=constants.UNKNOWN, error=f'[{type(self).__name__}] Failed loading skill: {e}')

		instructionsFile = self.getResource(f'instructions/{self.LanguageManager.activeLanguage}.md')
		if not instructionsFile.exists():
			instructionsFile = self.getResource(f'instructions/en.md')

		self._instructions = instructionsFile.read_text() if instructionsFile.exists() else ''

		self._name = self._installer['name']
		self._author = self._installer.get('author', constants.UNKNOWN)
		self._version = self._installer.get('version', '0.0.1')
		self._icon = self._installer.get('icon', 'fas fa-biohazard')
		self._aliceMinVersion = Version.fromString(self._installer.get('aliceMinVersion', '1.0.0-b4'))
		self._maintainers = self._installer.get('maintainers', list())
		self._description = self._installer.get('desc', '')
		self._category = self._installer.get('category', constants.UNKNOWN)
		self._conditions = self._installer.get('conditions', dict())
		self._updateAvailable = False
		self._modified = False
		self._active = False
		self._delayed = False
		self._required = False
		self._failedStarting = False
		self._databaseSchema = databaseSchema
		self._widgets = list()
		self._widgetTemplates = dict()
		self._deviceTypes = list()
		self._intentsDefinitions = dict()
		self._scenarioPackageName = ''
		self._scenarioPackageVersion = Version(mainVersion=0, updateVersion=0, hotfix=0)

		self._supportedIntents: Dict[str, Intent] = self.buildIntentList(supportedIntents)
		self.loadIntentsDefinition()

		self._utteranceSlotCleaner = re.compile('{(.+?):=>.+?}')
		self._myDevicesTemplates = dict()
		self._myDevices: Dict[str, Device] = dict()


	@property
	def failedStarting(self) -> bool:
		return self._failedStarting


	@property
	def myDevices(self) -> Dict[str, Device]:
		return self._myDevices


	@failedStarting.setter
	def failedStarting(self, value: bool):
		self._failedStarting = value


	def registerDeviceInstance(self, device: Device):
		if device.paired:
			self._myDevices[device.uid] = device


	def unregisterDeviceInstance(self, device: Device):
		self._myDevices.pop(device.uid, None)


	def getHtmlInstructions(self) -> flask.Markup:
		return flask.Markup(markdown(self._instructions))


	def addUtterance(self, text: str, intent: str, language: str = None) -> bool:
		"""
		Add the supplied utterance for a given skill to the dialogTemplate extending file of the
		current active language if no specific language is supplied.
		:param text:
		:param intent:
		:param language: default None will load the active Language from language manager
		:return:
		"""
		lang = language if language is not None else self.activeLanguage()
		file = self.getResource(f'dialogTemplate/{lang}.ext.json')
		file.touch()

		data: Dict = json.loads(file.read_text())
		data.setdefault('intents', dict())
		data['intents'].setdefault(intent, dict())
		data['intents'][intent].setdefault('utterances', list())

		utterances = data['intents'][intent]['utterances']
		if not text in utterances:
			utterances.append(text)
			data['intents'][intent]['utterances'] = utterances
			file.write_text(json.dumps(data, ensure_ascii=False, indent='\t'))
			return True

		return False


	def loadScenarioNodes(self) -> None:
		"""
		Load the scenario nodes (folder scenarioNodes) for Node-Red and store them in _scenarioPackageName
		:return:
		"""
		path = self.getResource('scenarioNodes/package.json')
		if not path.exists():
			return

		try:
			with path.open('r') as fp:
				data = json.load(fp)
				self._scenarioPackageName = data['name']
				self._scenarioPackageVersion = Version.fromString(data['version'])
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


	def loadWidgets(self) -> None:
		"""
		Load all .py files in the widgets folder and load them as instances of Widget.
		Loaded widget types are added to self._widgets
		:return:
		"""
		fp = self.getResource('widgets')
		if fp.exists():
			self.logInfo(f"Found **{len(list(fp.glob('*.py'))) - 1}** widget", plural='widget')
			for file in fp.glob('*.py'):
				if file.name.startswith('__'):
					continue

				self._widgets.append(Path(file).stem)
				self.loadWidgetConfigTemplate(Path(file).stem)


	def loadWidgetConfigTemplate(self, widgetType):
		"""
		Load the config file of the current widget type.
		The config has to be in the default alice json format containing the config value names, default value and value type.
		:param widgetType:
		:return:
		"""
		try:
			filepath = Path(f'skills/{self._name}/widgets/{widgetType}.config.template')
			if not filepath.exists():
				self.logInfo(f'![green](No widget config template for widget type {widgetType} found)')
				return

			data = json.loads(filepath.read_text())

			self._widgetTemplates[widgetType] = data
		except Exception as e:
			self.logError(f'Error loading widget config template for widget type **{widgetType}** {e}')


	def getWidgetTemplate(self, name: str) -> dict:
		"""
		Get the config template for the given widget type in the current skill instance.
		:param name:
		:return:
		"""
		if name in self._widgetTemplates:
			return self._widgetTemplates[name]
		else:
			return dict()


	def loadDeviceTypes(self) -> None:
		"""
		Load all .py files in the devices folder and load them as instances of DeviceType.
		Loaded devices types are added to self._deviceTypes
		:return:
		"""
		fp = self.getResource('devices')
		if fp.exists():
			self.logInfo(f"Found **{len(list(fp.glob('*.py'))) - 1}** device type", plural='type')
			for file in fp.glob('*.py'):
				if file.name.startswith('__'):
					continue

				self._deviceTypes.append(Path(file).stem)

				try:
					deviceImport = importlib.import_module(f'skills.{self.name}.devices.{file.stem}')
					klass: Device = getattr(deviceImport, file.stem)
					self.DeviceManager.registerDeviceType(self.name, klass.getDeviceTypeDefinition())
				except Exception as e:
					self.logError(f"Failed retrieving device type definition for device **{file.stem}** {e}")


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


	def supportedIntentsWithUtterances(self) -> dict:
		return {str(intent): self.getUtterancesByIntent(intent, True, True) for intent in self._supportedIntents}


	@property
	def widgets(self) -> list:
		return self._widgets


	@property
	def deviceTypes(self) -> list:
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
	def version(self) -> str:
		return self._version


	@version.setter
	def version(self, value: str):
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
	def modified(self) -> bool:
		return self._modified


	@modified.setter
	def modified(self, value: bool):
		"""
		As the skill has no writeToDB method and this is the only value that has to be saved right away
		a update of the value on the DB is performed. This should only occure manually triggered when the user starts to make local changes
		:param value:
		:return:
		"""
		self._modified = value
		self.SkillManager.setSkillModified(skillName=self.name, modified=self._modified)
		dbVal = 1 if value else 0
		self.DatabaseManager.update(tableName=self.SkillManager.DBTAB_SKILLS,
		                            callerName=self.SkillManager.name,
		                            row=('skillname', self.name),
		                            values={'modified': dbVal})


	@property
	def scenarioNodeName(self) -> str:
		return self._scenarioPackageName


	@property
	def scenarioNodeVersion(self) -> Version:
		return self._scenarioPackageVersion


	@property
	def icon(self) -> str:
		return self._icon


	@property
	def installFile(self) -> Path:
		return self._installFile


	@property
	def skillPath(self) -> Path:
		return self._skillPath


	@property
	def instructions(self) -> str:
		return self._instructions


	def hasScenarioNodes(self) -> bool:
		return self._scenarioPackageName != ''


	def subscribeIntents(self):
		self.MqttManager.subscribeSkillIntents(self._supportedIntents)


	def unsubscribeIntents(self):
		self.MqttManager.unsubscribeSkillIntents(self._supportedIntents)


	def notifyDevice(self, topic: str, deviceUid: str = ''):
		self.MqttManager.publish(topic=topic, payload={'uid': deviceUid})


	def authenticateIntent(self, session: DialogSession):
		intent = self._supportedIntents[session.message.topic]
		# Return if intent is for auth users only but the user is unknown
		if session.user == constants.UNKNOWN_USER:
			self.endDialog(
				sessionId=session.sessionId,
				text=self.TalkManager.randomTalk(talk='unknownUser', skill='system')
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

		self.loadDeviceTypes()
		self.loadWidgets()
		self.loadScenarioNodes()

		self._failedStarting = False
		self.logInfo(f'![green](Started!)')


	def onStop(self):
		self._active = False
		self.SkillManager.configureSkillIntents(self._name, False)
		self.logInfo(f'![green](Stopped)')
		self.broadcast(method=constants.EVENT_SKILL_STOPPED, exceptions=[self.name], propagateToSkills=True, skill=self)


	def onBooted(self) -> bool:
		if self.delayed:
			self.logInfo('Delayed start')
			self.ThreadManager.doLater(interval=5, func=self.onStart)

		return True


	def onSkillInstalled(self, **kwargs):
		self.onSkillUpdated(**kwargs)


	def onSkillUpdated(self, skill: str):
		if skill != self.name:
			return

		self._updateAvailable = False
		self.MqttManager.subscribeSkillIntents(self._supportedIntents)


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


	def databaseFetch(self, tableName: str, query: str, values: dict = None) -> List:
		return self.DatabaseManager.fetch(tableName=tableName, query=query, values=values, callerName=self.name)


	def databaseInsert(self, tableName: str, query: str = None, values: dict = None) -> int:
		return self.DatabaseManager.insert(tableName=tableName, query=query, values=values, callerName=self.name)


	def randomTalk(self, text: str, replace: Union[str, List] = None, skill: str = None) -> str:
		if not isinstance(replace, list):
			replace = [replace]

		talk = self.TalkManager.randomTalk(talk=text, skill=skill or self.name)

		if replace:
			talk = talk.format(*replace)
		return talk


	def getSkillInstance(self, skillName: str) -> AliceSkill:
		return self.SkillManager.getSkillInstance(skillName=skillName)


	def say(self, text: str, deviceUid: str = None, customData: dict = None, canBeEnqueued: bool = True):
		self.MqttManager.say(text=text, deviceUid=deviceUid, customData=customData, canBeEnqueued=canBeEnqueued)


	def ask(self, text: str, deviceUid: str = None, intentFilter: list = None, customData: dict = None, canBeEnqueued: bool = True, currentDialogState: str = '', probabilityThreshold: float = None):
		if currentDialogState:
			currentDialogState = f'{self.name}:{currentDialogState}'
		self.MqttManager.ask(text=text, deviceUid=deviceUid, intentFilter=intentFilter, customData=customData, canBeEnqueued=canBeEnqueued, currentDialogState=currentDialogState, probabilityThreshold=probabilityThreshold)


	def continueDialog(self, sessionId: str, text: str, customData: dict = None, intentFilter: list = None, slot: str = '', currentDialogState: str = '', probabilityThreshold: float = None):
		if currentDialogState:
			currentDialogState = f'{self.name}:{currentDialogState}'
		self.MqttManager.continueDialog(sessionId=sessionId, text=text, customData=customData, intentFilter=intentFilter, slot=slot, currentDialogState=currentDialogState, probabilityThreshold=probabilityThreshold)


	def endDialog(self, sessionId: str = '', text: str = '', deviceUid: str = ''):
		self.MqttManager.endDialog(sessionId=sessionId, text=text, deviceUid=deviceUid)


	def endSession(self, sessionId):
		self.MqttManager.endSession(sessionId=sessionId)


	def playSound(self, soundFilename: str, location: Path = None, sessionId: str = '', deviceUid: Union[str, List[Union[str, Device]]] = None):
		"""
		Sends audio chunks from the audio file over Mqtt. Note that instead of using a random "requestId"
		at the end of the topic, we	use the session id if available.
		:param soundFilename:
		:param location:
		:param sessionId:
		:param deviceUid:
		:return:
		"""
		session = self.DialogManager.getSession(sessionId=sessionId)
		if session:
			session.lastWasSoundPlayOnly = True

		self.MqttManager.playSound(soundFilename=soundFilename, location=location, sessionId=sessionId, deviceUid=deviceUid)


	def publish(self, topic: str, payload: dict = None, stringPayload: str = None, qos: int = 0, retain: bool = False):
		self.MqttManager.publish(topic=topic, payload=payload, stringPayload=stringPayload, qos=qos, retain=retain)


	def __repr__(self) -> str:
		return json.dumps(self.toDict())


	def __str__(self) -> str:
		return self.__repr__()


	def toDict(self) -> dict:
		return {
			'name'            : self._name,
			'author'          : self._author,
			'version'         : self._version,
			'modified'        : self._modified,
			'updateAvailable' : self._updateAvailable,
			'active'          : self._active,
			'delayed'         : self._delayed,
			'required'        : self._required,
			'databaseSchema'  : self._databaseSchema,
			'icon'            : self._icon,
			'instructions'    : self._instructions,
			'settings'        : self.ConfigManager.getSkillConfigs(self.name),
			'settingsTemplate': self.getSkillConfigsTemplate(),
			'description'     : self._description,
			'category'        : self._category,
			'aliceMinVersion' : str(self._aliceMinVersion),
			'maintainers'     : self._maintainers,
			'intents'         : self.supportedIntentsWithUtterances()
		}
