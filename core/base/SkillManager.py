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


import getpass
import importlib
import json
import os
import shutil
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests
from dulwich import errors as gitErrors, porcelain as git
from dulwich.repo import Repo

from core.ProjectAliceExceptions import AccessLevelTooLow, GithubNotFound, SkillInstanceFailed, SkillNotConditionCompliant, SkillStartDelayed, SkillStartingFailed
from core.base.SuperManager import SuperManager
from core.base.model import Intent
from core.base.model.AliceSkill import AliceSkill
from core.base.model.FailedAliceSkill import FailedAliceSkill
from core.base.model.GithubCloner import GithubCloner
from core.base.model.Manager import Manager
from core.base.model.Version import Version
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.util.Decorators import IfSetting, Online, deprecated
from core.webui.model.UINotificationType import UINotificationType


class SkillManager(Manager):
	DBTAB_SKILLS = 'skills'

	DATABASE = {
		DBTAB_SKILLS: [
			'skillName TEXT NOT NULL UNIQUE',
			'active INTEGER NOT NULL DEFAULT 1',
			'scenarioVersion TEXT NOT NULL DEFAULT "0.0.0"',
			'modified INTEGER NOT NULL DEFAULT 0'
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

		self._busyInstalling = None

		self._skillInstallThread: Optional[threading.Thread] = None
		self._supportedIntents = list()

		# This is a dict of the skills, with name: dict(status, install file, modified)
		self._skillList = dict()

		# These are dict of the skills, with name: skill instance
		self._activeSkills: Dict[str, AliceSkill] = dict()
		self._deactivatedSkills: Dict[str, AliceSkill] = dict()
		self._failedSkills: Dict[str, Union[AliceSkill, FailedAliceSkill]] = dict()

		self._postBootSkillActions = dict()


	def onStart(self):
		super().onStart()

		self._busyInstalling = self.ThreadManager.newEvent(name='skillInstallation', onSetCallback=self.notifyInstalling, onClearCallback=self.notifyFinishedInstalling)
		self._skillList = self._loadSkills()

		if not self._skillList:
			self.logInfo('Looks like a fresh install or skills were nuked. Let\'s install the basic skills!')
			self.downloadSkills(skills=self.BASE_SKILLS)
		elif sorted(list(self._skillList.keys())) != sorted(self.BASE_SKILLS):
			self.logInfo('Some required skills are missing, let\'s download them!')
			self.downloadSkills(skills=list(set(self.NEEDED_SKILLS) - set(list(self._skillList.keys()))))

		self._initSkills()

		for skillName in self._deactivatedSkills:
			self.configureSkillIntents(skillName=skillName, state=False)

		updates = self.checkForSkillUpdates()
		if updates:
			self.updateSkills(skills=updates)

		self.ConfigManager.loadCheckAndUpdateSkillConfigurations()

		self.startAllSkills()


	def notifyInstalling(self):
		self.MqttManager.mqttBroadcast(topic=constants.TOPIC_SYSTEM_UPDATE, payload={'sticky': True})


	def notifyFinishedInstalling(self):
		self.MqttManager.mqttBroadcast(topic='hermes/leds/clear')


	# noinspection SqlResolve
	def _loadSkills(self) -> Dict[str, Dict[str, Any]]:
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

		data = dict()
		for skill in skills.copy():
			try:
				installer = json.loads(Path(self.Commons.rootDir(), f'skills/{skill["skillName"]}/{skill["skillName"]}.install').read_text())
				data[skill['skillName']] = {
					'active'   : skill['active'],
					'modified' : skill['modified'] == 1,
					'installer': installer
				}
			except Exception as e:
				self.logError(f'Error loading skill **{skill["skillName"]}**: {e}')

		return dict(sorted(data.items()))


	def updateSkills(self, skills: Union[str, List[str]]):
		"""
		Updates skills to latest available version for this Alice version
		:param skills:
		:return:
		"""
		self._busyInstalling.set()

		if isinstance(skills, str):
			skills = [skills]

		for skillName in skills:
			try:
				repository = self.getSkillRepository(skillName=skillName)
				git.stash_push(repository)
				git.reset(repository, mode='hard')
				git.pull(repo=repository, refspecs=self.SkillStoreManager.getSkillUpdateTag(skillName=skillName))
			except Exception as e:
				self.logError(f'Error updating skill **{skillName}** : {e}')
				continue
		self._busyInstalling.clear()


	def downloadSkills(self, skills: Union[str, List[str]]):
		"""
		Clones skills
		:param skills:
		:return:
		"""
		self._busyInstalling.set()

		if isinstance(skills, str):
			skills = [skills]

		for skillName in skills:
			try:
				source = self.getGitRemoteSourceUrl(skillName=skillName, doAuth=False)
				repository = self.getSkillRepository(skillName=skillName)
				if not repository:
					repository = git.clone(source=source, target=self.getSkillDirectory(skillName=skillName), checkout=True)

				git.pull(repo=repository, refspecs=self.SkillStoreManager.getSkillUpdateTag(skillName=skillName))

				self._skillList[skillName] = {
					'active'   : 1,
					'modified' : 0,
					'installer': json.loads(Path(self.getSkillDirectory(skillName=skillName), f'{skillName}.install').read_text())
				}
			except GithubNotFound:
				if skillName in self.NEEDED_SKILLS:
					self._busyInstalling.clear()
					self.logFatal(f"Skill **{skillName}** is required but wasn't found in released skills, cannot continue")
					return
				else:
					self.logError(f'Skill "{skillName}" not found in released skills')
					continue
			except Exception as e:
				if skillName in self.NEEDED_SKILLS:
					self._busyInstalling.clear()
					self.logFatal(f'Error downloading skill **{skillName}** but skill is required, cannot continue: {e}')
					return
				else:
					self.logError(f'Error downloading skill "{skillName}": {e}')
					continue

		self._busyInstalling.clear()


	def loadSkillsFromDB(self) -> List:
		return self.databaseFetch(tableName='skills')


	def changeSkillStateInDB(self, skillName: str, newState: bool):
		# Changes the state of a skill in db and also deactivates widgets
		# and device types if state is False
		self.DatabaseManager.update(
			tableName='skills',
			callerName=self.name,
			values={
				'active': 1 if newState else 0
			},
			row=('skillName', skillName)
		)

		if not newState:
			self.WidgetManager.skillDeactivated(skillName=skillName)
			self.DeviceManager.skillDeactivated(skillName=skillName)


	def addSkillToDB(self, skillName: str, active: int = 1):
		self.DatabaseManager.replace(
			tableName='skills',
			values={'skillName': skillName, 'active': active}
		)


	# noinspection SqlResolve
	def removeSkillFromDB(self, skillName: str):
		self.DatabaseManager.delete(
			tableName='skills',
			callerName=self.name,
			query='DELETE FROM :__table__ WHERE skillName = :skill',
			values={'skill': skillName}
		)


	def onAssistantInstalled(self, **kwargs):
		argv = kwargs.get('skillsInfos', dict())
		if not argv:
			return

		for skillName, skill in argv.items():
			try:
				self._startSkill(skillName=skillName)
			except SkillStartDelayed:
				self.logInfo(f'Skill "{skillName}" start is delayed')
			except KeyError as e:
				self.logError(f'Skill "{skillName} not found, skipping: {e}')
				continue

			self._activeSkills[skillName].onBooted()

			self.broadcast(
				method=constants.EVENT_SKILL_UPDATED if skill['update'] else constants.EVENT_SKILL_INSTALLED,
				exceptions=[constants.DUMMY],
				skill=skillName
			)


	@property
	def supportedIntents(self) -> list:
		return self._supportedIntents


	@property
	def neededSkills(self) -> list:
		return self.NEEDED_SKILLS


	@property
	def activeSkills(self) -> Dict[str, AliceSkill]:
		return self._activeSkills


	@property
	def deactivatedSkills(self) -> Dict[str, AliceSkill]:
		return self._deactivatedSkills


	@property
	def failedSkills(self) -> dict:
		return self._failedSkills


	@property
	def allSkills(self) -> dict:
		return {**self._activeSkills, **self._deactivatedSkills, **self._failedSkills}


	@property
	def allWorkingSkills(self) -> dict:
		return {**self._activeSkills, **self._deactivatedSkills}


	def onBooted(self):
		self.skillBroadcast(constants.EVENT_BOOTED)
		self._finishInstall()

		if self._skillInstallThread:
			self._skillInstallThread.start()


	def dispatchMessage(self, session: DialogSession) -> bool:
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


	def _initSkills(self, onlyInit: str = '', reload: bool = False):
		"""
		Loops over the available skills, creates their instances
		:param onlyInit: If specified, will only init the given skill name
		:param reload: If the skill is already instantiated, performs a module reload, after an update per example.
		:return:
		"""

		for skillName, data in self._skillList.items():
			if onlyInit and skillName != onlyInit:
				continue

			self._activeSkills.pop(skillName, None)
			self._failedSkills.pop(skillName, None)
			self._deactivatedSkills.pop(skillName, None)

			try:
				if not data['active']:
					if skillName in self.NEEDED_SKILLS:
						self.logFatal(f"Skill {skillName} marked as disabled but it shouldn't be")
						return
					else:
						self.logInfo(f'Skill {skillName} is disabled')
				else:
					self.checkSkillConditions(data['installer'])

				skillInstance = self.instantiateSkill(skillName=skillName, reload=reload)
				if skillInstance:
					if skillName in self.NEEDED_SKILLS:
						skillInstance.required = True

					if data['active']:
						self._activeSkills[skillInstance.name] = skillInstance
					else:
						self._deactivatedSkills[skillName] = skillInstance

					skillInstance.modified = data.get('modified', False)
				else:
					if skillName in self.NEEDED_SKILLS:
						self.logFatal(f'The skill is required to continue...')
						return
					else:
						self._failedSkills[skillName] = FailedAliceSkill(data['installer'])
			except SkillNotConditionCompliant as e:
				if skillName in self.NEEDED_SKILLS:
					self.logFatal(f'Skill {skillName} does not comply to "{e.condition}" condition, offers only "{e.conditionValue}". The skill is required to continue')
					return
				else:
					self.logInfo(f'Skill {skillName} does not comply to "{e.condition}" condition, offers only "{e.conditionValue}"')
					self._failedSkills[skillName] = FailedAliceSkill(data['installer'])
					continue
			except Exception as e:
				self.logWarning(f'Something went wrong loading skill {skillName}: {e}')
				self._failedSkills[skillName] = FailedAliceSkill(data['installer'])
				continue


	# noinspection PyTypeChecker
	def instantiateSkill(self, skillName: str, skillResource: str = '', reload: bool = False) -> Optional[AliceSkill]:
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


	def onStop(self):
		super().onStop()

		for skillItem in self._activeSkills.values():
			skillItem.onStop()
			self.broadcast(method=constants.EVENT_SKILL_STOPPED, exceptions=[self.name], propagateToSkills=True, skill=self)


	def onQuarterHour(self):
		if self._busyInstalling.isSet() or self.ProjectAlice.restart or self.ProjectAlice.updating or self.NluManager.training:
			return

		updates = self.checkForSkillUpdates()
		if updates:
			self.updateSkills(skills=updates)


	def startAllSkills(self):
		supportedIntents = list()

		for skillName in self._activeSkills.copy():
			try:
				supportedIntents += self._startSkill(skillName)
			except SkillStartingFailed:
				continue
			except SkillStartDelayed:
				self.logInfo(f'Skill {skillName} start is delayed')

		supportedIntents = list(set(supportedIntents))
		self._supportedIntents = supportedIntents

		self.logInfo(f'Skills started. {len(supportedIntents)} intents supported')


	def _startSkill(self, skillName: str) -> dict:
		if skillName in self._activeSkills:
			skillInstance = self._activeSkills[skillName]
		elif skillName in self._deactivatedSkills:
			self._deactivatedSkills.pop(skillName, None)
			skillInstance = self.instantiateSkill(skillName=skillName)
			if skillInstance:
				self.activeSkills[skillName] = skillInstance
			else:
				return dict()
		elif skillName in self._failedSkills:
			skillInstance = self.instantiateSkill(skillName=skillName)
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
			self.broadcast(method=constants.EVENT_SKILL_STARTED, exceptions=[self.name], propagateToSkills=True, skill=self)
		except SkillStartingFailed:
			try:
				skillInstance.failedStarting = True
			except:
				self._failedSkills[skillName] = FailedAliceSkill(self._skillList[skillName]['installer'])
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

			self._failedSkills[skillName] = FailedAliceSkill(self._skillList[skillName]['installer'])

		return skillInstance.supportedIntents


	def isSkillActive(self, skillName: str) -> bool:
		if skillName in self._activeSkills:
			return self._activeSkills[skillName].active
		return False


	def getSkillInstance(self, skillName: str, silent: bool = False) -> Optional[AliceSkill]:
		if skillName in self._activeSkills:
			return self._activeSkills[skillName]
		elif skillName in self._deactivatedSkills:
			return self._deactivatedSkills[skillName]
		elif skillName in self._failedSkills:
			return self._failedSkills[skillName]
		else:
			if not silent:
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


	def deactivateSkill(self, skillName: str, persistent: bool = False):
		if skillName in self._activeSkills:
			skillInstance = self._activeSkills.pop(skillName)
			self._deactivatedSkills[skillName] = skillInstance
			skillInstance.onStop()
			self.broadcast(method=constants.EVENT_SKILL_STOPPED, exceptions=[self.name], propagateToSkills=True, skill=self)

			if persistent:
				self.changeSkillStateInDB(skillName=skillName, newState=False)
				self.logInfo(f'Deactivated skill "{skillName}" with persistence')
			else:
				self.logInfo(f'Deactivated skill "{skillName}" without persistence')
		else:
			self.logWarning(f'Skill "{skillName} is not active')


	def activateSkill(self, skillName: str, persistent: bool = False):
		if skillName not in self._deactivatedSkills and skillName not in self._failedSkills:
			self.logWarning(f'Skill "{skillName} is not deactivated or failed')
			return

		try:
			self._startSkill(skillName)

			if persistent:
				self.changeSkillStateInDB(skillName=skillName, newState=True)
				self.logInfo(f'Activated skill "{skillName}" with persistence')
			else:
				self.logInfo(f'Activated skill "{skillName}" without persistence')
		except:
			self.logError(f'Failed activating skill "{skillName}"')
			return


	def toggleSkillState(self, skillName: str, persistent: bool = False):
		if self.isSkillActive(skillName):
			self.deactivateSkill(skillName=skillName, persistent=persistent)
		else:
			self.activateSkill(skillName=skillName, persistent=persistent)


	@Online(catchOnly=True)
	@IfSetting(settingName='stayCompletelyOffline', settingValue=False)
	def checkForSkillUpdates(self, skillToCheck: str = None) -> List[str]:
		"""
		Check all installed skills for availability of updates.
		Includes failed skills but not inactive.
		:param skillToCheck:
		:return:
		"""
		self.logInfo('Checking for skill updates')
		skillsToUpdate = list()

		for skillName, data in self._skillList.items():
			if not data['active']:
				continue

			try:
				if skillToCheck and skillName != skillToCheck:
					continue

				remoteVersion = self.SkillStoreManager.getSkillUpdateVersion(skillName)
				localVersion = Version.fromString(self._skillList[skillName]['installer']['version'])
				if localVersion < remoteVersion:

					self.WebUINotificationManager.newNotification(
						typ=UINotificationType.INFO,
						notification='skillUpdateAvailable',
						key='skillUpdate_{}'.format(skillName),
						replaceBody=[skillName, str(remoteVersion)]
					)

					if data.get('modified', False):
						self.allSkills[skillName].updateAvailable = True
						self.logInfo(f'![blue]({skillName}) - Version {self._skillList[skillName]["installer"]["version"]} < {str(remoteVersion)} in {self.ConfigManager.getAliceConfigByName("skillsUpdateChannel")} - Locked for local changes!')
						continue

					self.logInfo(f'![yellow]({skillName}) - Version {self._skillList[skillName]["installer"]["version"]} < {str(remoteVersion)} in {self.ConfigManager.getAliceConfigByName("skillsUpdateChannel")}')

					if not self.ConfigManager.getAliceConfigByName('skillAutoUpdate'):
						if skillName in self.allSkills:
							self.allSkills[skillName].updateAvailable = True
					else:
						skillsToUpdate.append(skillName)
				else:
					if data.get('modified', False):
						self.logInfo(f'![blue]({skillName}) - Version {self._skillList[skillName]["installer"]["version"]} in {self.ConfigManager.getAliceConfigByName("skillsUpdateChannel")} - Locked for local changes!')
					else:
						self.logInfo(f'![green]({skillName}) - Version {self._skillList[skillName]["installer"]["version"]} in {self.ConfigManager.getAliceConfigByName("skillsUpdateChannel")}')

			except GithubNotFound:
				self.logInfo(f'![red](Skill **{skillName}**) is not available on Github. Deprecated or is it a dev skill?')

			except Exception as e:
				self.logError(f'Error checking updates for skill **{skillName}**: {e}')

		self.logInfo(f'Found {len(skillsToUpdate)} skill update', plural='update')
		return skillsToUpdate


	@Online(catchOnly=True)
	def _checkForSkillInstall(self):
		# Don't start the install timer from the main thread in case it's the first start
		if self._skillInstallThread:
			self.ThreadManager.newTimer(interval=10, func=self._checkForSkillInstall, autoStart=True)

		root = Path(self.Commons.rootDir(), constants.SKILL_INSTALL_TICKET_PATH)
		files = [f for f in root.iterdir() if f.suffix == '.install']

		if self._busyInstalling.isSet() or not files or self.ProjectAlice.restart or self.ProjectAlice.updating or self.NluManager.training:
			return

		self.logInfo(f'Found {len(files)} install ticket', plural='ticket')
		self._busyInstalling.set()

		skillsToBoot = dict()
		try:
			skillsToBoot = self._installSkillTickets(files)
		except Exception as e:
			self._logger.logError(f'Error installing skill: {e}')
		finally:
			if skillsToBoot and self.ProjectAlice.isBooted:
				self._finishInstall(skillsToBoot, True)
			else:
				self._postBootSkillActions = skillsToBoot.copy()

			self._busyInstalling.clear()


	def _finishInstall(self, skills: dict = None, startSkill: bool = False):
		if not skills and not self._postBootSkillActions:
			return

		if not skills and self._postBootSkillActions:
			skills = self._postBootSkillActions

		for skillName, info in skills.items():

			if startSkill:
				self._initSkills(onlyInit=skillName, reload=info['update'])
				self.ConfigManager.loadCheckAndUpdateSkillConfigurations(skillToLoad=skillName)

				try:
					self._startSkill(skillName)
				except SkillStartDelayed:
					# The skill start was delayed
					pass

			if info['update']:
				self.allSkills[skillName].onSkillUpdated(skill=skillName)
				self.MqttManager.mqttBroadcast(
					topic=constants.TOPIC_SKILL_UPDATED,
					payload={
						'skillName': skillName
					}
				)

				self.WebUINotificationManager.newNotification(
					typ=UINotificationType.INFO,
					notification='skillUpdated',
					key='skillUpdate_{}'.format(skillName),
					replaceBody=[skillName, self._skillList[skillName]['installer']['version']]
				)
			else:
				self.allSkills[skillName].onSkillInstalled(skill=skillName)
				self.MqttManager.mqttBroadcast(
					topic=constants.TOPIC_SKILL_INSTALLED,
					payload={
						'skillName': skillName
					}
				)

			self.allSkills[skillName].onBooted()

		self._postBootSkillActions = dict()
		self.AssistantManager.checkAssistant()


	@deprecated
	def _installSkillTickets(self, skills: list) -> dict:
		"""
		Installs the skills from found install tickets
		:param skills: list of tickets
		:return:
		"""
		root = Path(self.Commons.rootDir(), constants.SKILL_INSTALL_TICKET_PATH)
		skillsToBoot = dict()
		self.MqttManager.mqttBroadcast(topic=constants.TOPIC_SYSTEM_UPDATE, payload={'sticky': True})
		for file in skills:
			skillName = Path(file).stem

			self.logInfo(f'Now taking care of skill {skillName}')
			res = root / file

			try:
				installFile = json.loads(res.read_text())

				skillName = installFile['name']

				if not skillName:
					self.logError('Skill name to install not found, aborting to avoid casualties!')
					continue

				if skillName in self._skillList:
					installedVersion = Version.fromString(self._skillList[skillName]['installer']['version'])
					remoteVersion = Version.fromString(installFile['version'])

					if installedVersion >= remoteVersion:
						self.logWarning(f'Skill "{skillName}" is already installed and up to date, skipping')
						self.Commons.runRootSystemCommand(['rm', res])
						continue
					else:
						self.logWarning(f'Skill "{skillName}" installed but needs updating')
						updating = True

						self.MqttManager.mqttBroadcast(
							topic=constants.TOPIC_SKILL_UPDATING,
							payload={
								'skillName': skillName
							}
						)
				else:
					updating = False

				self.checkSkillConditions(installFile)

				try:
					skillRepository = self.getSkillRepository(skillName=skillName)
				except GithubNotFound:
					if self.ConfigManager.getAliceConfigByName('devMode'):
						if not Path(f'{self.Commons.rootDir}/skills/{skillName}').exists() or not \
								Path(f'{self.Commons.rootDir}/skills/{skillName}/{skillName.py}').exists() or not \
								Path(f'{self.Commons.rootDir}/skills/{skillName}/dialogTemplate').exists() or not \
								Path(f'{self.Commons.rootDir}/skills/{skillName}/talks').exists():
							self.logWarning(f'Skill "{skillName}" cannot be installed in dev mode due to missing base files')
						else:
							self._installSkill(res)
							skillsToBoot[skillName] = {
								'update': updating
							}
						continue
					else:
						self.logWarning(f'Skill "{skillName}" is not available on Github, cannot install')
						raise


				if updating:
					try:
						self._skillList[skillName].onStop()
					except Exception as e:
						self.logError(f'Error stopping "{skillName}" for update: {e}')
						raise

					git.stash_push(skillRepository)
					git.reset(skillRepository, mode='hard')

				try:
					git.pull(skillRepository, refspecs=self.SkillStoreManager.getSkillUpdateTag(skillName))
				except:
					pass

			#
			# try:
			# 	gitCloner.cloneSkill()
			# 	self.logInfo('Skill successfully downloaded')
			# 	self._installSkill(res)
			# 	skillsToBoot[skillName] = {
			# 		'update': updating
			# 	}
			# except (GithubTokenFailed, GithubRateLimit):
			# 	self.logError('Failed cloning skill')
			# 	raise
			# except GithubNotFound:
			# 	if self.ConfigManager.getAliceConfigByName('devMode'):
			# 		if not Path(f'{self.Commons.rootDir}/skills/{skillName}').exists() or not \
			# 				Path(f'{self.Commons.rootDir}/skills/{skillName}/{skillName.py}').exists() or not \
			# 				Path(f'{self.Commons.rootDir}/skills/{skillName}/dialogTemplate').exists() or not \
			# 				Path(f'{self.Commons.rootDir}/skills/{skillName}/talks').exists():
			# 			self.logWarning(f'Skill "{skillName}" cannot be installed in dev mode due to missing base files')
			# 		else:
			# 			self._installSkill(res)
			# 			skillsToBoot[skillName] = {
			# 				'update': updating
			# 			}
			# 		continue
			# 	else:
			# 		self.logWarning(f'Skill "{skillName}" is not available on Github, cannot install')
			# 		raise

			except SkillNotConditionCompliant as e:
				self.logInfo(f'Skill "{skillName}" does not comply to "{e.condition}" condition, required "{e.conditionValue}"')
				if res.exists():
					res.unlink()

				self.broadcast(
					method=constants.EVENT_SKILL_INSTALL_FAILED,
					exceptions=self._name,
					skill=skillName
				)

			except Exception:
				self.logError(f'Failed installing skill "{skillName}"')
				if res.exists():
					res.unlink()

				self.broadcast(
					method=constants.EVENT_SKILL_INSTALL_FAILED,
					exceptions=self.name,
					skill=skillName
				)
				raise

		return skillsToBoot


	def getSkillDirectory(self, skillName: str) -> Path:
		return Path(self.Commons.rootDir()) / 'skills' / skillName


	def getSkillRepository(self, skillName: str, directory: str = None) -> Optional[Repo]:
		"""
		Returns a dulwich repository object for the given skill
		:param skillName:
		:param directory: where to clone that skill, if not standard directory
		:return:
		"""

		if not directory:
			directory = self.getSkillDirectory(skillName=skillName)

		try:
			return Repo(directory)
		except gitErrors.NotGitRepository:
			return None


	def getGitRemoteSourceUrl(self, skillName: str, doAuth: bool = True) -> str:
		"""
		Returns the url for the skillname, taking into account if the user provided github auth
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


	def _installSkill(self, res: Path):
		try:
			installFile = json.loads(res.read_text())
			pipReqs = installFile.get('pipRequirements', list())
			sysReqs = installFile.get('systemRequirements', list())
			scriptReq = installFile.get('script')
			directory = Path(self.Commons.rootDir()) / 'skills' / installFile['name']

			for requirement in pipReqs:
				self.logInfo(f'Installing pip requirement: {requirement}')
				self.Commons.runSystemCommand(['./venv/bin/pip3', 'install', requirement])

			for requirement in sysReqs:
				self.logInfo(f'Installing system requirement: {requirement}')
				self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', requirement])

			if scriptReq:
				self.logInfo('Running post install script')
				self.Commons.runRootSystemCommand(['chmod', '+x', str(directory / scriptReq)])
				self.Commons.runRootSystemCommand([str(directory / scriptReq)])

			self.addSkillToDB(installFile['name'])
			self._skillList[installFile['name']] = {
				'active'   : 1,
				'installer': installFile,
				'modified' : False
			}

			os.unlink(str(res))

			if installFile.get('rebootAfterInstall', False):
				self.Commons.runRootSystemCommand('sudo shutdown -r now'.split())
				return

		except Exception:
			raise


	def checkSkillConditions(self, installer: dict = None) -> bool:
		conditions = {
			'aliceMinVersion': installer['aliceMinVersion'],
			**installer.get('conditions', dict())
		}

		notCompliant = 'Skill is not compliant'

		if 'aliceMinVersion' in conditions and \
				Version.fromString(conditions['aliceMinVersion']) > Version.fromString(constants.VERSION):
			raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition='Alice minimum version', conditionValue=conditions['aliceMinVersion'])

		for conditionName, conditionValue in conditions.items():
			if conditionName == 'lang' and self.LanguageManager.activeLanguage not in conditionValue:
				raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'online':
				if conditionValue and self.ConfigManager.getAliceConfigByName('stayCompletelyOffline') \
						or not conditionValue and not self.ConfigManager.getAliceConfigByName('stayCompletelyOffline'):
					raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'skill':
				for requiredSkill in conditionValue:
					if requiredSkill in self._skillList and not self._skillList[requiredSkill]['active']:
						raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition=conditionName, conditionValue=conditionValue)
					elif requiredSkill not in self._skillList:
						self.logInfo(f'Skill {installer["name"]} has another skill as dependency, adding download')
						if not self.downloadInstallTicket(requiredSkill):
							raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'notSkill':
				for excludedSkill in conditionValue:
					author, name = excludedSkill.split('/')
					if name in self._skillList and self._skillList[name]['active']:
						raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'asrArbitraryCapture':
				if conditionValue and not self.ASRManager.asr.capableOfArbitraryCapture:
					raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'activeManager':
				for manager in conditionValue:
					if not manager:
						continue

					man = SuperManager.getInstance().getManager(manager)
					if not man or not man.isActive:
						raise SkillNotConditionCompliant(message=notCompliant, skillName=installer['name'], condition=conditionName, conditionValue=conditionValue)

		return True


	def configureSkillIntents(self, skillName: str, state: bool):
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
			self.logWarning(f'Intent configuration failed: {e}')


	def isIntentInUse(self, intent: Intent, filtered: list) -> bool:
		skills = self.allWorkingSkills
		return any(intent in skill.supportedIntents for name, skill in skills.items() if name not in filtered)


	def removeSkill(self, skillName: str):
		if skillName not in self.allSkills:
			return

		if skillName in self._activeSkills:
			self._activeSkills[skillName].onStop()
			self.broadcast(method=constants.EVENT_SKILL_STOPPED, exceptions=[self.name], propagateToSkills=True, skill=self)

		self.broadcast(method=constants.EVENT_SKILL_DELETED, exceptions=[self.name], propagateToSkills=True, skill=skillName)

		self.MqttManager.mqttBroadcast(
			topic=constants.TOPIC_SKILL_DELETED,
			payload={
				'skillName': skillName
			}
		)

		self._skillList.pop(skillName, None)
		self._activeSkills.pop(skillName, None)
		self._deactivatedSkills.pop(skillName, None)
		self._failedSkills.pop(skillName, None)

		self.removeSkillFromDB(skillName=skillName)
		shutil.rmtree(Path(self.Commons.rootDir(), 'skills', skillName))

		self.AssistantManager.checkAssistant()


	def reloadSkill(self, skillName: str):
		self.logInfo(f'Reloading skill "{skillName}"')

		if skillName in self._activeSkills:
			self._activeSkills[skillName].onStop()
			self.broadcast(method=constants.EVENT_SKILL_STOPPED, exceptions=[self.name], propagateToSkills=True, skill=self)

		self._initSkills(onlyInit=skillName, reload=True)

		self.AssistantManager.checkAssistant()

		self._startSkill(skillName=skillName)


	def allScenarioNodes(self) -> Dict[str, tuple]:
		ret = dict()
		for skillName, skillInstance in self._activeSkills.items():
			if not skillInstance.hasScenarioNodes():
				continue

			ret[skillName] = (skillInstance.scenarioNodeName, skillInstance.scenarioNodeVersion, skillInstance.getResource('scenarioNodes'))

		return ret


	def skillScenarioNode(self, skillName: str) -> Optional[Path]:
		if skillName not in self.allWorkingSkills:
			return None

		return self.allWorkingSkills[skillName].getResource('scenarioNodes')


	def getSkillScenarioVersion(self, skillName: str) -> Version:
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
		shutil.rmtree(Path(self.Commons.rootDir(), 'skills'))
		Path(self.Commons.rootDir(), 'skills').mkdir()

		for skillName in self._skillList:
			self.removeSkillFromDB(skillName=skillName)

		self._activeSkills = dict()
		self._deactivatedSkills = dict()
		self._failedSkills = dict()
		self._skillList = dict()


	def createNewSkill(self, skillDefinition: dict) -> bool:
		try:
			self.logInfo(f'Creating new skill "{skillDefinition["name"]}"')

			skillName = skillDefinition['name'].capitalize()

			localDirectory = Path('/home', getpass.getuser(), f'ProjectAlice/skills/{skillName}')
			if localDirectory.exists():
				raise Exception("Skill name exists locally")

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
				'pipreq'            : [req.strip() for req in skillDefinition.get('pipreq', "").split(',')],
				'sysreq'            : [req.strip() for req in skillDefinition.get('sysreq', "").split(',')],
				'widgets'           : widgets,
				'scenarioNodes'     : scenarioNodes,
				'devices'           : devices,
				'outputDestination' : str(Path(self.Commons.rootDir()) / 'skills' / skillName),
				'conditions'        : conditions
			}

			dump = Path(f'/tmp/{skillName}.json')
			dump.write_text(json.dumps(data, ensure_ascii=False))

			self.Commons.runSystemCommand(['./venv/bin/pip', 'install', '--upgrade', 'projectalice-sk'])
			self.Commons.runSystemCommand(['./venv/bin/projectalice-sk', 'create', '--file', f'{str(dump)}'])
			self.logInfo(f'Created **{skillName}** skill')

			# todo: ugly..
			data['name'] = data['skillName']
			data['author'] = data['username']
			data['desc'] = data['description']
			# ok, version never filled in frontend and every skill should be created in initial version
			data['version'] = '0.0.1'

			self._failedSkills[skillName] = FailedAliceSkill(data)
			self._skillList[skillName] = {
				'active'   : False,
				'modified' : True,
				'installer': data
			}
			self._failedSkills[skillName].modified = True

			return True
		except Exception as e:
			self.logError(f'Error creating new skill: {e}')
			return False


	def uploadSkillToGithub(self, skillName: str, skillDesc: str) -> bool:
		try:
			self.logInfo(f'Uploading {skillName} to Github')

			skillName = skillName[0].upper() + skillName[1:]

			localDirectory = Path('/home', getpass.getuser(), f'ProjectAlice/skills/{skillName}')
			if not localDirectory.exists():
				raise Exception("Local skill doesn't exist")

			data = {
				'name'       : f'skill_{skillName}',
				'description': skillDesc,
				'has-issues' : True,
				'has-wiki'   : False
			}
			req = requests.post('https://api.github.com/user/repos', data=json.dumps(data), auth=GithubCloner.getGithubAuth())

			if req.status_code != 201:
				raise Exception("Couldn't create the repository on Github")

			self.Commons.runSystemCommand(['rm', '-rf', f'{str(localDirectory)}/.git'])
			self.Commons.runSystemCommand(['git', '-C', str(localDirectory), 'init'])

			self.Commons.runSystemCommand(['git', 'config', '--global', 'user.email', 'githubbot@projectalice.io'])
			self.Commons.runSystemCommand(['git', 'config', '--global', 'user.name', 'githubbot@projectalice.io'])

			remote = f'https://{self.ConfigManager.getAliceConfigByName("githubUsername")}:{self.ConfigManager.getAliceConfigByName("githubToken")}@github.com/{self.ConfigManager.getAliceConfigByName("githubUsername")}/skill_{skillName}.git'
			self.Commons.runSystemCommand(['git', '-C', str(localDirectory), 'remote', 'add', 'origin', remote])

			self.Commons.runSystemCommand(['git', '-C', str(localDirectory), 'add', '--all'])
			self.Commons.runSystemCommand(['git', '-C', str(localDirectory), 'commit', '-m', '"Initial upload by Project Alice Skill Kit"'])
			self.Commons.runSystemCommand(['git', '-C', str(localDirectory), 'push', '--set-upstream', 'origin', 'master'])

			url = f'https://github.com/{self.ConfigManager.getAliceConfigByName("githubUsername")}/skill_{skillName}.git'
			self.logInfo(f'Skill uploaded! You can find it on {url}')
			return True
		except Exception as e:
			self.logWarning(f'Something went wrong uploading skill to Github: {e}')
			return False


	def downloadInstallTicket(self, skillName: str, isUpdate: bool = False) -> bool:
		try:
			tmpFile = Path(self.Commons.rootDir(), f'system/skillInstallTickets/{skillName}.install')
			if not self.Commons.downloadFile(
					url=f'{constants.GITHUB_RAW_URL}/skill_{skillName}/{self.SkillStoreManager.getSkillUpdateTag(skillName)}/{skillName}.install',
					dest=str(tmpFile.with_suffix('.tmp'))
			):
				raise Exception

			if not isUpdate:
				requests.get(f'https://skills.projectalice.ch/{skillName}')

			shutil.move(tmpFile.with_suffix('.tmp'), tmpFile)
			return True
		except Exception as e:
			self.logError(f'Error downloading install ticket for skill "{skillName}": {e}')
			return False


	def setSkillModified(self, skillName: str, modified: bool):
		self._skillList[skillName][modified] = modified
