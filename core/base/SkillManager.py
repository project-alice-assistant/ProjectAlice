#  Copyright (c) 2021
#
#  This file, SkillManager.py, is part of Project Alice.
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
#  Last modified: 2021.08.02 at 06:12:17 CEST


import traceback

import importlib
import json
import requests
import shutil
from contextlib import suppress
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from AliceGit import Exceptions as GitErrors
from AliceGit.Exceptions import NotGitRepository, PathNotFoundException
from AliceGit.Git import Repository
from core.ProjectAliceExceptions import AccessLevelTooLow, GithubNotFound, SkillInstanceFailed, SkillNotConditionCompliant, SkillStartDelayed, SkillStartingFailed
from core.base.SuperManager import SuperManager
from core.base.model import Intent
from core.base.model.AliceSkill import AliceSkill
from core.base.model.FailedAliceSkill import FailedAliceSkill
from core.base.model.Manager import Manager
from core.base.model.Version import Version
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.util.Decorators import IfSetting, Online, deprecated
from core.util.model.AliceEvent import AliceEvent
from core.webui.model.UINotificationType import UINotificationType


class SkillManager(Manager):
	DBTAB_SKILLS = 'skills'

	DATABASE = {
		DBTAB_SKILLS: [
			'skillName TEXT NOT NULL UNIQUE',
			'active INTEGER NOT NULL DEFAULT 1',
			'scenarioVersion TEXT NOT NULL DEFAULT "0.0.0"'
		]
	}

	BASE_SKILLS = [
		'AliceCore',
		'ContextSensitive',
		'DateDayTimeYear',
		'RedQueen',
		'Telemetry'
	]

	NEEDED_SKILLS = [
		'AliceCore',
		'ContextSensitive',
		'RedQueen'
	]


	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)

		self._busyInstalling: Optional[AliceEvent] = None
		self._supportedIntents: List[Dict[str, Intent]] = list()

		# This is a list of the skill names installed
		self._skillList: List[str] = list()

		# These are dict of the skills, with name: skill instance
		self._activeSkills: Dict[str, AliceSkill] = dict()
		self._deactivatedSkills: Dict[str, AliceSkill] = dict()
		self._failedSkills: Dict[str, Union[AliceSkill, FailedAliceSkill]] = dict()


	@property
	def supportedIntents(self) -> List[Dict]:
		"""
		Returns a list of all supported intents
		:return:
		"""
		return self._supportedIntents


	@property
	def neededSkills(self) -> List[str]:
		"""
		List of skills that are needed for Alice to start
		:return:
		"""
		return self.NEEDED_SKILLS


	@property
	def activeSkills(self) -> Dict[str, AliceSkill]:
		"""
		Returns skills that inited and are active
		:return:
		"""
		return self._activeSkills


	@property
	def deactivatedSkills(self) -> Dict[str, AliceSkill]:
		"""
		Returns skills that inited but are disabled by user
		:return:
		"""
		return self._deactivatedSkills


	@property
	def failedSkills(self) -> Dict[str, FailedAliceSkill]:
		"""
		Returns skills that failed init
		:return:
		"""
		return self._failedSkills


	@property
	def allSkills(self) -> Dict[str, Union[AliceSkill, FailedAliceSkill]]:
		"""
		Returns all skill that inited. This might not contain skills that are physically present but weren't inited
		:return:
		"""
		return {**self._activeSkills, **self._deactivatedSkills, **self._failedSkills}


	@property
	def skillList(self) -> List:
		"""
		Returns all skills present in the skill directory. These might not be inited, might have failed etc etc
		:return:
		"""
		return self._skillList


	@property
	def allWorkingSkills(self) -> Dict[str, AliceSkill]:
		"""
		Returns a list of skills that are functional, but might be activated or deactivated. These skills passed init
		:return:
		"""
		return {**self._activeSkills, **self._deactivatedSkills}


	def onStart(self):
		super().onStart()

		self._busyInstalling = self.ThreadManager.newEvent(name='skillInstallation', onSetCallback=self.notifyInstalling, onClearCallback=self.notifyFinishedInstalling)
		self._skillList = self._loadSkills()

		if not self._skillList:
			self.logInfo('Looks like a fresh install or skills were nuked. Let\'s install the basic skills!')
			self.installSkills(skills=self.BASE_SKILLS)

		for skill in self.NEEDED_SKILLS:
			if skill not in self._skillList:
				self.logInfo('Some required skills are missing, let\'s download them!')
				self.installSkills(skills=list(set(self.NEEDED_SKILLS) - set(self._skillList)))
				break

		updates = self.checkForSkillUpdates()
		if updates:
			self.updateSkills(skills=updates, withSkillRestart=False)

		self.initSkills()

		for skillName in self._deactivatedSkills:
			self.configureSkillIntents(skillName=skillName, state=False)

		self.startAllSkills()


	def onBooted(self):
		self.skillBroadcast(constants.EVENT_BOOTED)


	def onStop(self):
		super().onStop()

		for skillName in list(self._activeSkills.keys()):
			self.stopSkill(skillName=skillName)


	def onQuarterHour(self):
		if self._busyInstalling.is_set() or self.ProjectAlice.restart or self.ProjectAlice.updating or self.NluManager.training:
			return

		updates = self.checkForSkillUpdates()
		if updates:
			self.updateSkills(skills=updates)


	def notifyInstalling(self):
		"""
		Sends a MQTT message to notify that Alice is updating
		:return:
		"""
		self.MqttManager.mqttBroadcast(topic=constants.TOPIC_SYSTEM_UPDATE, payload={'sticky': True})


	def notifyFinishedInstalling(self):
		"""
			Sends a MQTT message to notify that Alice finished installing something
			:return:
		"""
		self.MqttManager.mqttBroadcast(topic=constants.TOPIC_HLC_CLEAR_LEDS)


	# noinspection SqlResolve
	def _loadSkills(self) -> List[str]:
		"""
		Loads skills present on the disk and checks if they are declared in DB and cleans offenders
		Loads skills that are in DB and check if they are on the disk and cleans offenders
		Returns a sorted list of potentially usable skill names
		:return:
		"""
		skills = self.loadSkillsFromDB()
		skills = [skill['skillName'] for skill in skills]

		# First, make sure the skills installed are in database
		# if not, inject them
		physicalSkills = [skill.stem for skill in Path(self.Commons.rootDir(), 'skills').glob('**/*.install')]
		for file in physicalSkills:
			if file not in skills:
				if self.ConfigManager.getAliceConfigByName('devMode'):
					self.logWarning(f'Skill "{file}" is not declared in database, fixing this')
					self.addSkillToDB(file)
				else:
					self.logWarning(f'Skill "{file}" is not declared in database, ignoring it')

		# Next, check that database declared skills are still existing, using the first database load
		# If not, cleanup skills table
		for skill in skills:
			if skill not in physicalSkills:
				self.logWarning(f'Skill "{skill}" declared in database but is not existing, cleaning this')
				self.removeSkillFromDB(skillName=skill)

		# Now that we are clean, reload the skills from database
		# Those represent the skills we have
		skills = self.loadSkillsFromDB()

		data = list()
		for skill in skills:
			try:
				if not self.getSkillDirectory(skill['skillName']).exists():
					raise Exception('Skill directory not existing')
				data.append(skill['skillName'])
			except Exception as e:
				self.logError(f'Error loading skill **{skill["skillName"]}**: {e}')

		return sorted(data)


	def loadSkillsFromDB(self) -> List[Dict[str, Any]]:
		"""
		Loads skills from the database
		:return:
		"""
		return self.databaseFetch(tableName='skills')


	def addSkillToDB(self, skillName: str, active: int = 1):
		"""
		Adds given skill to database
		:param skillName:
		:param active:
		:return:
		"""
		self.DatabaseManager.replace(
			tableName='skills',
			values={'skillName': skillName, 'active': active}
		)


	# noinspection SqlResolve
	def removeSkillFromDB(self, skillName: str):
		"""
		Removes given skill from database
		:param skillName:
		:return:
		"""
		self.DatabaseManager.delete(
			tableName='skills',
			callerName=self.name,
			query='DELETE FROM :__table__ WHERE skillName = :skill',
			values={'skill': skillName}
		)


	def installSkills(self, skills: Union[str, List[str]], startSkill: bool = False):
		"""
		Installs the given skills
		:param skills: Either a list of skill names to install or a single skill name
		:param startSkill: If the skill should be immediately started
		:return:
		"""
		self._busyInstalling.set()
		if isinstance(skills, str):
			skills = [skills]

		for skillName in skills:
			try:
				try:
					repository = self.getSkillRepository(skillName=skillName)
				except:
					try:
						repositories = self.downloadSkills(skills=skillName)
						repository = repositories.get(skillName, None)
					except SkillNotConditionCompliant:
						continue

				if not repository:
					raise Exception(f'Failed downloading skill **{skillName}** for some unknown reason')

				installFile = json.loads(repository.file(f'{skillName}.install').read_text())
				pipReqs     = installFile.get('pipRequirements', list())
				sysReqs     = installFile.get('systemRequirements', list())
				scriptReq   = installFile.get('script')

				self.checkSkillConditions(installFile)

				for requirement in pipReqs:
					self.logInfo(f'Installing pip requirement: {requirement}')
					self.Commons.runSystemCommand(['./venv/bin/pip3', 'install', requirement])

				for requirement in sysReqs:
					self.logInfo(f'Installing system requirement: {requirement}')
					self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', requirement])

				if scriptReq:
					self.logInfo('Running post install script')
					req = repository.file(scriptReq)
					if not req:
						self.logWarning(f'Missing post install script **{str(req)}** as declared in install file')
						continue
					self.Commons.runRootSystemCommand(['chmod', '+x', str(req)])
					self.Commons.runRootSystemCommand([str(req)])

				self.addSkillToDB(skillName)
				self._skillList.append(skillName)

				if installFile.get('rebootAfterInstall', False):
					self.Commons.runRootSystemCommand('sudo shutdown -r now'.split())
					break
				elif startSkill:
					self.initSkills(onlyInit=skillName)
					self.startSkill(skillName=skillName)
			except SkillNotConditionCompliant:
				self.broadcast(
					method=constants.EVENT_SKILL_INSTALL_FAILED,
					exceptions=self._name,
					propagateToSkills=True,
					skill=skillName
				)
			except Exception as e:
				self.logError(f'Error installing skill **{skillName}**: {e}')
				self.broadcast(
					method=constants.EVENT_SKILL_INSTALL_FAILED,
					exceptions=[constants.DUMMY],
					propagateToSkills=True,
					skill=skillName
				)
			else:
				self.broadcast(
					method=constants.EVENT_SKILL_INSTALLED,
					exceptions=[constants.DUMMY],
					propagateToSkills=True,
					skill=skillName
				)

		self._busyInstalling.clear()


	def getSkillRepository(self, skillName: str, directory: str = None) -> Optional[Repository]:
		"""
		Returns a Git object for the given skill
		:param skillName:
		:param directory: where to look for that skill, if not standard directory
		:return:
		"""

		if not directory:
			directory = self.getSkillDirectory(skillName=skillName)

		try:
			return Repository(directory=directory)
		except:
			raise


	def downloadSkills(self, skills: Union[str, List[str]]) -> Optional[Dict]:
		"""
		Clones skills. Existence of the skill on line is checked
		:param skills:
		:return: Dict: a dict of created repositories
		"""
		if isinstance(skills, str):
			skills = [skills]

		repositories = dict()

		for skillName in skills:
			try:
				tag = self.SkillStoreManager.getSkillUpdateTag(skillName=skillName)
				response = requests.get(f'{constants.GITHUB_RAW_URL}/skill_{skillName}/{tag}/{skillName}.install')
				if response.status_code != 200:
					raise GithubNotFound

				self.logInfo(f'Now downloading **{skillName}** version **{tag}**')

				with suppress(): # Increment download counter
					requests.get(f'https://skills.projectalice.ch/{skillName}')

				installFile = response.json()

				if not self.ConfigManager.getAliceConfigByName('devMode'):
					self.checkSkillConditions(installer=installFile)

				source = self.getGitRemoteSourceUrl(skillName=skillName, doAuth=False)

				try:
					repository = self.getSkillRepository(skillName=skillName)
				except PathNotFoundException:
					repository = Repository.clone(url=source, directory=self.getSkillDirectory(skillName=skillName), makeDir=True)
				except NotGitRepository:
					shutil.rmtree(self.getSkillDirectory(skillName=skillName), ignore_errors=True)
					repository = Repository.clone(url=source, directory=self.getSkillDirectory(skillName=skillName), makeDir=True)
				except:
					raise

				repository.checkout(tag=tag)
				repositories[skillName] = repository
			except GithubNotFound:
				if skillName in self.NEEDED_SKILLS:
					self._busyInstalling.clear()
					self.logFatal(f"Skill **{skillName}** is required but wasn't found in released skills, cannot continue")
					return repositories
				else:
					self.logError(f'Skill "{skillName}" not found in released skills')
					continue
			except SkillNotConditionCompliant as e:
				if self.notCompliantSkill(skillName=skillName, exception=e):
					continue
				else:
					self._busyInstalling.clear()
					return repositories
			except Exception as e:
				if skillName in self.NEEDED_SKILLS:
					self._busyInstalling.clear()
					self.logFatal(f'Error downloading skill **{skillName}** and it is required, cannot continue: {e}')
					return repositories
				else:
					self.logError(f'Error downloading skill "{skillName}": {e}')
					continue
		return repositories


	def notCompliantSkill(self, skillName: str,  exception: SkillNotConditionCompliant) -> bool:
		"""
		Print out the fact a skill is not compliant and return false if Alice cannot continue as it's a needed skill
		:param skillName
		:param exception:
		:return:
		"""
		if skillName in self.NEEDED_SKILLS:
			self.logFatal(f'Skill {skillName} does not comply to "{exception.condition}" condition, offers only "{exception.conditionValue}". The skill is required to continue')
			return False
		else:
			self.logInfo(f'Skill {skillName} does not comply to "{exception.condition}" condition, offers only "{exception.conditionValue}"')
			return True


	def getSkillDirectory(self, skillName: str) -> Path:
		"""
		Returns the full path to a skill
		:param skillName:
		:return:
		"""
		return Path(self.Commons.rootDir()) / 'skills' / skillName


	def getGitRemoteSourceUrl(self, skillName: str, doAuth: bool = True) -> str:
		"""
		Returns the url for the skill name, taking into account if the user provided github auth
		This does check if the remote exists and raises an exception in case it does not
		:param skillName:
		:param doAuth: Pull, clone, fetch, non oauth requests, aren't concerned by rate limit
		:return:
		"""
		tokenPrefix = ''
		if doAuth:
			auth = self.Commons.getGithubAuth()
			if auth:
				tokenPrefix = f'{auth[0]}:{auth[1]}@'

		url = f'{constants.GITHUB_URL}/skill_{skillName}.git'
		if tokenPrefix:
			url = url.replace('://', f'://{tokenPrefix}')

		response = requests.get(url=url)
		if response.status_code != 200:
			raise GithubNotFound

		return url


	def initSkills(self, onlyInit: str = '', reload: bool = False):
		"""
		Initializing skills by checking their condition compliance and instantiating them.
		Does check if a skill fails and is required
		:param onlyInit: If specified, will only init the given skill name
		:param reload: If the skill is already instantiated, performs a module reload, after an update per example.
		:return:
		"""

		for skillName in self._skillList:
			if onlyInit and skillName != onlyInit:
				continue

			self._activeSkills.pop(skillName, None)
			self._failedSkills.pop(skillName, None)
			self._deactivatedSkills.pop(skillName, None)

			installFilePath = self.getSkillInstallFilePath(skillName=skillName)
			if not installFilePath.exists():
				if skillName in self.NEEDED_SKILLS:
					self.logFatal(f'Cannot find skill install file for skill **{skillName}**. The skill is required to continue')
					return
				else:
					self.logWarning(f'Cannot find skill install file for skill **{skillName}**, skipping.')
					continue
			else:
				installFile = json.loads(installFilePath.read_text())

			try:
				skillActiveState = self.isSkillActive(skillName=skillName)
				if not skillActiveState:
					if skillName in self.NEEDED_SKILLS:
						self.logFatal(f"Skill {skillName} marked as disabled but it cannot be")
						return
					else:
						self.logInfo(f'Skill {skillName} is disabled')
				else:
					self.checkSkillConditions(installFile)

				skillInstance = self.instantiateSkill(skillName=skillName, reload=reload)
				if skillInstance:
					if skillName in self.NEEDED_SKILLS:
						skillInstance.required = True

					if skillActiveState:
						self._activeSkills[skillInstance.name] = skillInstance
					else:
						self._deactivatedSkills[skillName] = skillInstance

					self.ConfigManager.loadCheckAndUpdateSkillConfigurations(skillToLoad=skillName)
				else:
					if skillName in self.NEEDED_SKILLS:
						self.logFatal(f'The skill is required to continue...')
						return
					else:
						self._failedSkills[skillName] = FailedAliceSkill(installFile)
			except SkillNotConditionCompliant as e:
				if self.notCompliantSkill(skillName=skillName, exception=e):
					self._failedSkills[skillName] = FailedAliceSkill(installFile)
					self.changeSkillStateInDB(skillName=skillName, newState=False)
					continue
				else:
					return
			except Exception as e:
				self.logWarning(f'Something went wrong loading skill {skillName}: {e}')
				if skillName in self.NEEDED_SKILLS:
					self.logFatal(f'The skill is required to continue...')
					return
				else:
					self._failedSkills[skillName] = FailedAliceSkill(installFile)
					self.changeSkillStateInDB(skillName=skillName, newState=False)
					continue


	def getSkillInstallFilePath(self, skillName: str) -> Path:
		"""
		Returns the full path to a skill's install file
		:param skillName:
		:return:
		"""
		return self.getSkillDirectory(skillName=skillName) / f'{skillName}.install'


	# noinspection PyTypeChecker
	def instantiateSkill(self, skillName: str, skillResource: str = '', reload: bool = False) -> Optional[AliceSkill]:
		"""
		Instantiates the given skill at the given path
		:param skillName:
		:param skillResource:
		:param reload:
		:return:
		"""
		instance: Optional[AliceSkill] = None
		skillResource = skillResource or skillName

		try:
			skillImport = importlib.import_module(f'skills.{skillName}.{skillResource}')

			if reload:
				skillImport = importlib.reload(skillImport)

			klass = getattr(skillImport, skillName)
			instance: AliceSkill = klass()
		except ImportError as e:
			self.logError(f"Couldn't import skill {skillName}.{skillResource}: {e}")
			traceback.print_exc()
		except AttributeError as e:
			self.logError(f"Couldn't find main class for skill {skillName}.{skillResource}: {e}")
		except SkillInstanceFailed:
			self.logError(f"Couldn't instanciate skill {skillName}.{skillResource}")
		except Exception as e:
			self.logError(f"Unknown error instantiating {skillName}.{skillResource}: {e} {traceback.print_exc()}")

		return instance


	def isSkillActive(self, skillName: str) -> bool:
		"""
		Returns true or false depending if the skill is declared as active
		:param skillName:
		:return:
		"""
		if skillName in self._activeSkills:
			return self._activeSkills[skillName].active
		elif skillName in self._failedSkills or skillName in self._deactivatedSkills:
			return False
		elif skillName in self._skillList:
			# noinspection SqlResolve
			row = self.databaseFetch(tableName=self.DBTAB_SKILLS, query='SELECT active FROM :__table__ WHERE skillName = :skillName LIMIT 1', values={'skillName': skillName})
			if not row:
				return False
			return int(row[0]['active']) == 1
		return False


	def checkSkillConditions(self, installer: dict = None, checkOnly=False) -> Union[bool, List[Dict[str, str]]]:
		"""
		Checks if the given skill is compliant to it's conditions
		:param installer:
		:param checkOnly: Do not perform any other action (download other skill, etc) but checking conditions
		:return:
		"""
		conditions = {
			'aliceMinVersion': installer['aliceMinVersion'],
			**installer.get('conditions', dict())
		}

		notCompliant = 'Skill is not compliant'
		notCompliantRules = list()

		if 'aliceMinVersion' in conditions and Version.fromString(conditions['aliceMinVersion']) > Version.fromString(constants.VERSION):
			if not checkOnly:
				raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition='Alice minimum version', conditionValue=conditions['aliceMinVersion'])
			else:
				notCompliantRules.append({'Alice version': conditions['aliceMinVersion']})

		for conditionName, conditionValue in conditions.items():
			if conditionName == 'lang' and self.LanguageManager.activeLanguage not in conditionValue:
				if not checkOnly:
					raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition=conditionName, conditionValue=conditionValue)
				else:
					notCompliantRules.append({conditionName: conditionValue})

			elif conditionName == 'online':
				if conditionValue and self.ConfigManager.getAliceConfigByName('stayCompletelyOffline') or not conditionValue and not self.ConfigManager.getAliceConfigByName('stayCompletelyOffline'):
					if not checkOnly:
						raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition=conditionName, conditionValue=conditionValue)
					else:
						notCompliantRules.append({conditionName: conditionValue})

			elif conditionName == 'skill':
				for requiredSkill in conditionValue:
					if requiredSkill in self._skillList and not self.isSkillActive(skillName=installer['name']):
						if not checkOnly:
							raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition=conditionName, conditionValue=conditionValue)
						else:
							notCompliantRules.append({conditionName: conditionValue})
					elif requiredSkill not in self._skillList:
						if not checkOnly:
							self.logInfo(f'Skill {installer["name"]} has another skill as dependency, adding download')
							try:
								self.downloadSkills(skills=requiredSkill)
							except:
								raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition=conditionName, conditionValue=conditionValue)
						else:
							notCompliantRules.append({conditionName: conditionValue})

			elif conditionName == 'notSkill':
				for excludedSkill in conditionValue:
					author, name = excludedSkill.split('/')
					if name in self._skillList and self.isSkillActive(skillName=installer['name']):
						if not checkOnly:
							raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition=conditionName, conditionValue=conditionValue)
						else:
							notCompliantRules.append({conditionName: conditionValue})

			elif conditionName == 'asrArbitraryCapture':
				if conditionValue and not self.ASRManager.asr.capableOfArbitraryCapture:
					if not checkOnly:
						raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition=conditionName, conditionValue=conditionValue)
					else:
						notCompliantRules.append({conditionName: conditionValue})

			elif conditionName == 'activeManager':
				for manager in conditionValue:
					if not manager:
						continue

					man = SuperManager.getInstance().getManager(manager)
					if not man or not man.isActive:
						if not checkOnly:
							raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition=conditionName, conditionValue=conditionValue)
						else:
							notCompliantRules.append({conditionName: conditionValue})

		return True if not checkOnly else notCompliantRules


	def updateSkills(self, skills: Union[str, List[str]], withSkillRestart: bool = True):
		"""
		Updates skills to latest available version for this Alice version
		:param skills:
		:param withSkillRestart: Whether or not to start the skill after updating it
		:return:
		"""
		self._busyInstalling.set()

		if isinstance(skills, str):
			skills = [skills]

		for skillName in skills:
			self.logInfo(f'Now updating skill **{skillName}**')
			self.stopSkill(skillName=skillName)
			self._failedSkills.pop(skillName, None)

			try:
				repository = self.getSkillRepository(skillName=skillName)
				repository.fetch(force=True)
				repository.checkout(tag=self.SkillStoreManager.getSkillUpdateTag(skillName=skillName), force=True)
			except Exception as e:
				self.logError(f'Error updating skill **{skillName}** : {e}')
				continue

			self.broadcast(
				method=constants.EVENT_SKILL_UPDATED,
				exceptions=[constants.DUMMY],
				propagateToSkills=True,
				skill=skillName
			)

			self.initSkills(onlyInit=skillName, reload=True)
			if skillName in self.activeSkills:
				self.logInfo(f'Updated skill **{skillName}** to version **{self.activeSkills[skillName].version}**')

			if withSkillRestart:
				self.startSkill(skillName=skillName)

		self._busyInstalling.clear()


	def stopSkill(self, skillName: str) -> Optional[AliceSkill]:
		"""
		Stops the given skill
		:param skillName:
		:return:
		"""
		skill = None
		if skillName in self._activeSkills:
			skill = self._activeSkills.pop(skillName, None)
			skill.onStop()
			self.broadcast(
				method=constants.EVENT_SKILL_STOPPED,
				exceptions=[constants.DUMMY],
				propagateToSkills=True,
				skill=skillName
			)
		return skill


	def configureSkillIntents(self, skillName: str, state: bool):
		"""
		Subs or unsubs the skill intents. Alice only recognizes subscribed intents
		:param skillName:
		:param state:
		:return:
		"""
		try:
			skills = self.allWorkingSkills
			confs = [{
				'intentId': intent.justTopic if isinstance(intent, Intent.Intent) else intent.split('/')[-1],
				'enable'  : state
			} for intent in skills[skillName].supportedIntents if not self.isIntentInUse(intent=intent, filtered=[skillName])]

			self.MqttManager.configureIntents(confs)

			if state:
				skills[skillName].subscribeIntents()
			else:
				skills[skillName].unsubscribeIntents()
		except Exception as e:
			if not self.ProjectAlice.shuttingDown:
				self.logWarning(f'Intent configuration failed: {e}')


	def isIntentInUse(self, intent: Intent, filtered: list) -> bool:
		"""
		Returns whether an intent is used by any WORKING skill
		:param intent:
		:param filtered:
		:return:
		"""
		skills = self.allWorkingSkills
		return any(intent in skill.supportedIntents for name, skill in skills.items() if name not in filtered)


	def startAllSkills(self):
		"""
		Starts all the discovered skills
		:return:
		"""
		supportedIntents = list()

		for skillName in self._activeSkills.copy():
			try:
				supportedIntents += self.startSkill(skillName)
			except SkillStartingFailed:
				continue
			except SkillStartDelayed:
				self.logInfo(f'Skill {skillName} start is delayed')

		supportedIntents = list(set(supportedIntents))
		self._supportedIntents = supportedIntents

		self.logInfo(f'Skills started. {len(supportedIntents)} intents supported')


	def startSkill(self, skillName: str) -> Dict:
		"""
		Starts a skill
		:param skillName:
		:return:
		"""
		if skillName in self._activeSkills:
			skillInstance = self._activeSkills[skillName]
		elif skillName in self._deactivatedSkills or skillName in self._failedSkills:
			if skillName in self._failedSkills:
				skill = self._failedSkills.pop(skillName, None)
			else:
				skill = self._deactivatedSkills.pop(skillName, None)

			try:
				skillInstance = self.instantiateSkill(skillName=skillName)
				self.checkSkillConditions(installer=json.loads(self.getSkillInstallFilePath(skillName=skillName).read_text()))
			except:
				self._failedSkills[skillName] = FailedAliceSkill(json.loads(skill.getResource(f'{skillName}.install').read_text()))
				return dict()

			if skillInstance:
				self.activeSkills[skillName] = skillInstance
			else:
				return dict()
		else:
			self.logWarning(f'Skill "{skillName}" is unknown')
			return dict()

		try:
			skillInstance.onStart()
			if self.ProjectAlice.isBooted:
				skillInstance.onBooted()

			self.broadcast(
				method=constants.EVENT_SKILL_STARTED,
				exceptions=[constants.DUMMY],
				propagateToSkills=True,
				skill=skillName
			)
		except SkillStartingFailed:
			try:
				skillInstance.failedStarting = True
			except:
				self._failedSkills[skillName] = FailedAliceSkill(skillInstance.installer)
		except SkillStartDelayed:
			raise
		except Exception as e:
			self.logError(f'- Couldn\'t start skill "{skillName}". Error: {e}')
			traceback.print_exc()

			try:
				self.deactivateSkill(skillName=skillName)
			except:
				self._activeSkills.pop(skillName, None)
				self._deactivatedSkills.pop(skillName, None)

			self._failedSkills[skillName] = FailedAliceSkill(skillInstance.installer)

		return skillInstance.supportedIntents


	def deactivateSkill(self, skillName: str, persistent: bool = False) -> bool:
		"""
		Deactivates a skill and broadcasts it
		:param skillName:
		:param persistent:
		:return:
		"""
		if skillName in self._activeSkills:
			skillInstance = self.stopSkill(skillName=skillName)
			if skillInstance:
				self._deactivatedSkills[skillName] = skillInstance
				self.broadcast(
					method=constants.EVENT_SKILL_DEACTIVATED,
					exceptions=[constants.DUMMY],
					propagateToSkills=True,
					skill=skillInstance
				)

			if persistent:
				self.changeSkillStateInDB(skillName=skillName, newState=False)
				self.logInfo(f'Deactivated skill "{skillName}" with persistence')
			else:
				self.logInfo(f'Deactivated skill "{skillName}" without persistence')

			return True
		else:
			self.logWarning(f'Skill "{skillName} is not active')
			return False


	def activateSkill(self, skillName: str, persistent: bool = False) -> bool:
		"""
		Activates a skill and broadcasts it
		:param skillName:
		:param persistent:
		:return:
		"""
		if skillName not in self._deactivatedSkills and skillName not in self._failedSkills:
			self.logWarning(f'Skill "{skillName} is not deactivated or failed')
			return False

		try:
			self.startSkill(skillName)

			if skillName not in self._activeSkills:
				return False

			if persistent:
				self.changeSkillStateInDB(skillName=skillName, newState=True)
				self.logInfo(f'Activated skill "{skillName}" with persistence')
			else:
				self.logInfo(f'Activated skill "{skillName}" without persistence')

			self.broadcast(
				method=constants.EVENT_SKILL_ACTIVATED,
				exceptions=[constants.DUMMY],
				propagateToSkills=True,
				skill=self.activeSkills[skillName]
			)
			return True
		except:
			self.logError(f'Failed activating skill "{skillName}"')
			return False


	def toggleSkillState(self, skillName: str, persistent: bool = False):
		"""
		Activate the given skill if deactivated or deactivates the given skill if actived
		:param skillName:
		:param persistent:
		:return:
		"""
		if self.isSkillActive(skillName):
			self.deactivateSkill(skillName=skillName, persistent=persistent)
		else:
			self.activateSkill(skillName=skillName, persistent=persistent)


	def changeSkillStateInDB(self, skillName: str, newState: bool):
		"""
		Updates the given skill DB entry state
		:param skillName:
		:param newState:
		:return:
		"""
		self.DatabaseManager.update(
			tableName='skills',
			callerName=self.name,
			values={
				'active': 1 if newState else 0
			},
			row=('skillName', skillName)
		)


	def dispatchMessage(self, session: DialogSession) -> bool:
		"""
		Dispatches a MQTT message to skills until one accepts it and returns True. If the intent wasn't consumed, return False
		:param session:
		:return:
		"""
		for skillName, skillInstance in self._activeSkills.items():
			try:
				consumed = skillInstance.onMessageDispatch(session)
			except AccessLevelTooLow:
				# The command was recognized but required higher access level
				return True
			except Exception as e:
				self.logError(f'Error dispatching message "{session.intentName.split("/")[-1]}" to {skillInstance.name}: {e}')
				self.MqttManager.endDialog(
					sessionId=session.sessionId,
					text=self.TalkManager.randomTalk(talk='error', skill='system')
				)
				traceback.print_exc()
				return True

			if consumed:
				self.logDebug(f'The intent "{session.intentName.split("/")[-1]}" was consumed by {skillName}')

				if self.MultiIntentManager.isProcessing(session.sessionId):
					self.MultiIntentManager.processNextIntent(session=session)

				return True

		if self.MultiIntentManager.isProcessing(session.sessionId):
			self.MultiIntentManager.processNextIntent(session=session)
			return True

		return False


	@Online(catchOnly=True)
	@IfSetting(settingName='stayCompletelyOffline', settingValue=False)
	def checkForSkillUpdates(self, skillToCheck: str = None) -> List[str]:
		"""
		Checks all installed skills for availability of updates.
		Includes failed skills but not inactive.
		:param skillToCheck:
		:return:
		"""
		self.logInfo('Checking for skill updates')
		skillsToUpdate = list()

		for skillName in self._skillList:
			try:
				if skillToCheck and skillName != skillToCheck:
					continue

				installer = json.loads(self.getSkillInstallFilePath(skillName=skillName).read_text())

				remoteVersion = self.SkillStoreManager.getSkillUpdateVersion(skillName)
				localVersion = Version.fromString(installer['version'])
				if localVersion < remoteVersion:

					self.WebUINotificationManager.newNotification(
						typ=UINotificationType.INFO,
						notification='skillUpdateAvailable',
						key='skillUpdate_{}'.format(skillName),
						replaceBody=[skillName, str(remoteVersion)]
					)

					if self.isSkillUserModified(skillName=skillName) and self.ConfigManager.getAliceConfigByName('devMode'):
						if skillName in self.allSkills:
							self.allSkills[skillName].updateAvailable = True

						self.logInfo(f'![blue]({skillName}) - Version {installer["version"]} < {str(remoteVersion)} in {self.ConfigManager.getAliceConfigByName("skillsUpdateChannel")} - Locked for local changes!')
						continue

					self.logInfo(f'![yellow]({skillName}) - Version {installer["version"]} < {str(remoteVersion)} in {self.ConfigManager.getAliceConfigByName("skillsUpdateChannel")}')

					if not self.ConfigManager.getAliceConfigByName('skillAutoUpdate'):
						if skillName in self.allSkills:
							self.allSkills[skillName].updateAvailable = True
					else:
						skillsToUpdate.append(skillName)
				else:
					if self.isSkillUserModified(skillName=skillName) and self.ConfigManager.getAliceConfigByName('devMode'):
						self.logInfo(f'![blue]({skillName}) - Version {installer["version"]} in {self.ConfigManager.getAliceConfigByName("skillsUpdateChannel")} - Locked for local changes!')
					else:
						self.logInfo(f'![green]({skillName}) - Version {installer["version"]} in {self.ConfigManager.getAliceConfigByName("skillsUpdateChannel")}')

			except GithubNotFound:
				self.logInfo(f'![red](Skill **{skillName}**) is not available on Github. Deprecated or is it a dev skill?')

			except Exception as e:
				self.logError(f'Error checking updates for skill **{skillName}**: {e}')

		self.logInfo(f'Found {len(skillsToUpdate)} skill update', plural='update')
		return skillsToUpdate


	def getSkillInstance(self, skillName: str, silent: bool = False) -> Optional[AliceSkill]:
		"""
		Returns a skill instance, if available
		:param skillName:
		:param silent:
		:return:
		"""
		if skillName in self._activeSkills:
			return self._activeSkills[skillName]
		elif skillName in self._deactivatedSkills:
			return self._deactivatedSkills[skillName]
		elif skillName in self._failedSkills:
			return self._failedSkills[skillName]
		else:
			if not silent and not self.ProjectAlice.shuttingDown:
				self.logWarning(f'Skill "{skillName}" does not exist in skills manager')

			return None


	def skillBroadcast(self, method: str, filterOut: list = None, **kwargs):
		"""
		Broadcasts a call to the given method on every skill
		:param filterOut: array, skills not to broadcast to
		:param method: str, the method name to call on every skill
		:return:
		"""

		if not method.startswith('on'):
			method = f'on{method[0].capitalize() + method[1:]}'

		for skillName, skillInstance in self._activeSkills.items():

			if filterOut and skillName in filterOut:
				continue

			try:
				func = getattr(skillInstance, method, None)
				if func:
					func(**kwargs)

				func = getattr(skillInstance, 'onEvent', None)
				if func:
					func(event=method, **kwargs)

			except TypeError as e:
				self.logWarning(f'Failed to broadcast event {method} to {skillName}: {e}')


	def removeSkill(self, skillName: str):
		"""
		Deletes a skill completely
		:param skillName:
		:return:
		"""
		if skillName not in self.allSkills:
			return

		self.deactivateSkill(skillName=skillName, persistent=False)
		self.broadcast(
			method=constants.EVENT_SKILL_DELETED,
			exceptions=[self.name],
			propagateToSkills=True,
			skill=skillName
		)

		self._skillList.remove(skillName)
		self._activeSkills.pop(skillName, None)
		self._deactivatedSkills.pop(skillName, None)
		self._failedSkills.pop(skillName, None)

		self.removeSkillFromDB(skillName=skillName)

		with suppress():
			repo = self.getSkillRepository(skillName=skillName)
			repo.destroy()

		self.AssistantManager.checkAssistant()


	def reloadSkill(self, skillName: str):
		"""
		Reloads a skill
		:param skillName:
		:return:
		"""
		self.logInfo(f'Reloading skill "{skillName}"')

		self.stopSkill(skillName=skillName)
		self.initSkills(onlyInit=skillName, reload=True)
		self.AssistantManager.checkAssistant()
		self.startSkill(skillName=skillName)


	def allScenarioNodes(self) -> Dict[str, tuple]:
		"""
		Returns list of Node-Red nodes added by skills
		:return:
		"""
		ret = dict()
		for skillName, skillInstance in self._activeSkills.items():
			if not skillInstance.hasScenarioNodes():
				continue

			ret[skillName] = (skillInstance.scenarioNodeName, skillInstance.scenarioNodeVersion, skillInstance.getResource('scenarioNodes'))

		return ret


	def skillScenarioNode(self, skillName: str) -> Optional[Path]:
		"""
		Returns  list of Node-Red nodes for the given skill
		:param skillName:
		:return:
		"""
		if skillName not in self.allWorkingSkills:
			return None

		return self.allWorkingSkills[skillName].getResource('scenarioNodes')


	def getSkillScenarioVersion(self, skillName: str) -> Version:
		"""
		Return Node Red scenario node version for the given skill
		:param skillName:
		:return:
		"""
		if skillName not in self._skillList:
			return Version.fromString('0.0.0')
		else:
			# noinspection SqlResolve
			query = 'SELECT * FROM :__table__ WHERE skillName = :skillName'
			data = self.DatabaseManager.fetch(tableName='skills', query=query, values={'skillName': skillName}, callerName=self.name)
			if not data:
				return Version.fromString('0.0.0')

			return Version.fromString(data[0]['scenarioVersion'])


	def wipeSkills(self):
		"""
		Lazy version to delete all skill, remove the entire directory and recreate it
		:return:
		"""
		shutil.rmtree(Path(self.Commons.rootDir(), 'skills'))
		Path(self.Commons.rootDir(), 'skills').mkdir()

		for skillName in self._skillList:
			self.removeSkillFromDB(skillName=skillName)

		self._activeSkills = dict()
		self._deactivatedSkills = dict()
		self._failedSkills = dict()
		self._skillList = dict()


	def isSkillUserModified(self, skillName: str) -> bool:
		"""
		Checks git status to see if the skill was modified from original online
		:param skillName:
		:return:
		"""
		try:
			repository = self.getSkillRepository(skillName=skillName)
			return repository.isDirty()
		except:
			return False


	def createNewSkill(self, skillDefinition: dict) -> bool:
		"""
		Used to create a new skill by the usr
		:param skillDefinition:
		:return:
		"""
		try:
			self.logInfo(f'Creating new skill "{skillDefinition["name"]}"')

			skillName = skillDefinition['name'].capitalize()

			localDirectory = self.getSkillDirectory(skillName=skillName)
			if localDirectory.exists():
				raise Exception('Skill name exists locally')

			supportedLanguages = [
				'en'
			]
			if skillDefinition.get('fr', 'false') == 'true':
				supportedLanguages.append('fr')
			if skillDefinition.get('de', 'false') == 'true':
				supportedLanguages.append('de')
			if skillDefinition.get('it', 'false') == 'true':
				supportedLanguages.append('it')
			if skillDefinition.get('pl', 'false') == 'true':
				supportedLanguages.append('pl')
			if skillDefinition.get('pt', 'false') == 'true':
				supportedLanguages.append('pt')
			if skillDefinition.get('pt_br', 'false') == 'true':
				supportedLanguages.append('pt_br')

			conditions = {
				'lang': supportedLanguages
			}

			if skillDefinition.get('conditionOnline', False):
				conditions['online'] = True

			if skillDefinition.get('conditionASRArbitrary', False):
				conditions['asrArbitraryCapture'] = True

			if skillDefinition.get('conditionSkill', []):
				conditions['skill'] = [skill.strip() for skill in skillDefinition['conditionSkill'].split(',')]

			if skillDefinition.get('conditionNotSkill', []):
				conditions['notSkill'] = [skill.strip() for skill in skillDefinition['conditionNotSkill'].split(',')]

			if skillDefinition.get('conditionActiveManager', []):
				conditions['activeManager'] = [manager.strip() for manager in skillDefinition['conditionActiveManager'].split(',')]

			if skillDefinition.get('widgets', []):
				widgets = [self.Commons.toPascalCase(widget).strip() for widget in skillDefinition['widgets'].split(',')]
			else:
				widgets = list()

			if skillDefinition.get('nodes', []):
				scenarioNodes = [self.Commons.toPascalCase(node).strip() for node in skillDefinition['nodes'].split(',')]
			else:
				scenarioNodes = list()

			if skillDefinition.get('devices', []):
				devices = [self.Commons.toPascalCase(device).strip() for device in skillDefinition['devices'].split(',')]
			else:
				devices = list()

			data = {
				'username'          : self.ConfigManager.getAliceConfigByName('githubUsername'),
				'skillName'         : skillName.capitalize(),
				'description'       : skillDefinition['description'],
				'category'          : skillDefinition['category'],
				'speakableName'     : skillDefinition['speakableName'],
				'langs'             : supportedLanguages,
				'createInstructions': skillDefinition.get('instructions', False),
				'pipreq'            : [req.strip() for req in skillDefinition.get('pipreq', '').split(',')],
				'sysreq'            : [req.strip() for req in skillDefinition.get('sysreq', '').split(',')],
				'widgets'           : widgets,
				'scenarioNodes'     : scenarioNodes,
				'devices'           : devices,
				'outputDestination' : str(localDirectory),
				'conditions'        : conditions
			}

			dump = Path(f'/tmp/{skillName}.json')
			dump.write_text(json.dumps(data, ensure_ascii=False))

			result = self.Commons.runSystemCommand(['./venv/bin/projectalice-sk', 'create', '--file', f'{str(dump)}'])
			if result.stderr:
				raise Exception('SK create failed')

			self._skillList.append(skillName)
			self.addSkillToDB(skillName=skillName)

			self.logInfo(f'Created **{skillName}** skill')

			return True
		except Exception as e:
			self.logError(f'Error creating new skill: {e}')
			return False


	def uploadSkillToGithub(self, skillName: str, skillDesc: str) -> bool:
		"""
		sends skill name oin Github
		:param skillName:
		:param skillDesc:
		:return:
		"""
		try:
			self.logInfo(f'Uploading {skillName} to Github')

			skillName = skillName[0].upper() + skillName[1:]

			try:
				repository = self.getSkillRepository(skillName=skillName)
			except GitErrors.PathNotFoundException:
				raise Exception(f"Local skill **{skillName}** doesn't exist")
			except GitErrors.NotGitRepository:
				raise Exception(f'Skill **{skillName}** found but is not a git repository')


			auth = self.ConfigManager.githubAuth
			self.Commons.runSystemCommand(f'./venv/bin/projectalice-sk uploadToGithub --token {auth[1]} --author {auth[0]} --path {str(repository.path)} --desc {skillDesc}')

			url = f'https://github.com/{auth[0]}/skill_{skillName}.git'
			self.logInfo(f'Skill uploaded! You can find it on {url}')
			return True
		except Exception as e:
			self.logWarning(f'Something went wrong uploading skill to Github: {e}')
			return False


	@deprecated
	def setSkillModified(self, skillName: str, modified: bool):
		return



