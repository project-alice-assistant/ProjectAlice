import getpass
import importlib
import json
import threading
import traceback
from pathlib import Path
from typing import Dict, Optional

import os
import requests
import shutil

from core.ProjectAliceExceptions import AccessLevelTooLow, GithubNotFound, GithubRateLimit, GithubTokenFailed, SkillNotConditionCompliant, SkillStartDelayed, SkillStartingFailed
from core.base.SuperManager import SuperManager
from core.base.model import Intent
from core.base.model.AliceSkill import AliceSkill
from core.base.model.FailedAliceSkill import FailedAliceSkill
from core.base.model.GithubCloner import GithubCloner
from core.base.model.Manager import Manager
from core.base.model.Version import Version
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.util.Decorators import IfSetting, Online


class SkillManager(Manager):

	NEEDED_SKILLS = [
		'AliceCore',
		'ContextSensitive',
		'RedQueen'
	]

	DATABASE = {
		'skills' : [
			'skillName TEXT NOT NULL UNIQUE',
			'active INTEGER NOT NULL DEFAULT 1'
		],
		'widgets': [
			'parent TEXT NOT NULL UNIQUE',
			'name TEXT NOT NULL UNIQUE',
			'posx INTEGER NOT NULL',
			'posy INTEGER NOT NULL',
			'height INTEGER NOT NULL',
			'width INTEGER NOT NULL',
			'state TEXT NOT NULL',
			'options TEXT NOT NULL',
			'custStyle TEXT NOT NULL',
			'zindex INTEGER'
		]
	}

	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)

		self._busyInstalling = None

		self._skillInstallThread: Optional[threading.Thread] = None
		self._supportedIntents = list()

		# This is only a dict of the skills, with name: dict(status, install file)
		self._skillList = dict()

		# These are dict of the skills, with name: skill instance
		self._activeSkills: Dict[str, AliceSkill] = dict()
		self._deactivatedSkills: Dict[str, AliceSkill] = dict()
		self._failedSkills: Dict[str, FailedAliceSkill] = dict()

		self._widgets = dict()


	def onStart(self):
		super().onStart()

		self._busyInstalling = self.ThreadManager.newEvent('skillInstallation')

		self._skillList = self._loadSkills()

		# If it's the first time we start, don't delay skill install and do it on main thread
		if not self._skillList:
			self.logInfo('Looks like a fresh install or skills were nuked. Let\'s install the basic skills!')
			self._checkForSkillInstall()
		elif self.checkForSkillUpdates():
			self._checkForSkillInstall()

		self._skillInstallThread = self.ThreadManager.newThread(name='SkillInstallThread', target=self._checkForSkillInstall, autostart=False)
		self._initSkills()

		for skillName in self._deactivatedSkills:
			self.configureSkillIntents(skillName=skillName, state=False)

		self.ConfigManager.loadCheckAndUpdateSkillConfigurations()

		self.startAllSkills()


	# noinspection SqlResolve
	def _loadSkills(self) -> dict:
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
		# If not, cleanup both skills and widgets tables
		for skill in skills:
			if skill not in physicalSkills:
				self.logWarning(f'Skill "{skill}" declared in database but is not existing, cleaning this')
				self.DatabaseManager.delete(
					tableName='skills',
					callerName=self.name,
					query='DELETE FROM :__table__ WHERE skillName = :skill',
					values={'skill': skill}
				)
				self.DatabaseManager.delete(
					tableName='widgets',
					callerName=self.name,
					query='DELETE FROM :__table__ WHERE parent = :skill',
					values={'skill': skill}
				)
				self.DeviceManager.removeDeviceTypesForSkill(skillName=skill)

		# Now that we are clean, reload the skills from database
		# Those represent the skills we have
		skills = self.loadSkillsFromDB()

		data = dict()
		for skill in skills:
			installer = json.loads(Path(self.Commons.rootDir(), f'skills/{skill["skillName"]}/{skill["skillName"]}.install').read_text())
			data[skill['skillName']] = {
				'active'   : skill['active'],
				'installer': installer
			}

		return dict(sorted(data.items()))


	def loadSkillsFromDB(self) -> list:
		return self.databaseFetch(
			tableName='skills',
			method='all'
		)


	def changeSkillStateInDB(self, skillName: str, newState: bool):
		# Changes the state of a skill in db and also deactivates widgets if state is False
		self.DatabaseManager.update(
			tableName='skills',
			callerName=self.name,
			values={
				'active': 1 if newState else 0
			},
			row=('skillName', skillName)
		)

		if not newState:
			self.DatabaseManager.update(
				tableName='widgets',
				callerName=self.name,
				values={
					'state' : 0,
					'posx'  : 0,
					'posy'  : 0,
					'zindex': 9999
				},
				row=('parent', skillName)
			)


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

		self.DatabaseManager.delete(
			tableName='widgets',
			callerName=self.name,
			query='DELETE FROM :__table__ WHERE parent = :skill',
			values={'skill': skillName}
		)

		self.DeviceManager.removeDeviceTypesForSkill(skillName=skillName)


	def onSnipsAssistantInstalled(self, **kwargs):
		self.MqttManager.mqttBroadcast(topic='hermes/leds/clear')

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


	def sortWidgetZIndexes(self):
		widgets = dict()
		for skillName, widgetList in self._widgets.items():
			for widget in widgetList.values():
				widgets[int(widget.zindex)] = widget

		counter = 0
		for i in sorted(widgets.keys()):
			if widgets[i].state == 0:
				widgets[i].zindex = -1
				widgets[i].saveToDB()
				continue

			widgets[i].zindex = counter
			counter += 1
			widgets[i].saveToDB()


	@property
	def widgets(self) -> dict:
		return self._widgets


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

			if self.MultiIntentManager.isProcessing(session.sessionId):
				self.MultiIntentManager.processNextIntent(session.sessionId)
				return True

			elif consumed:
				self.logDebug(f'The intent "{session.intentName.split("/")[-1]}" was consumed by {skillName}')
				return True

		return False


	def _initSkills(self, loadOnly: str = '', reload: bool = False):
		for skillName, data in self._skillList.items():
			if loadOnly and skillName != loadOnly:
				continue

			self._activeSkills.pop(skillName, None)
			self._failedSkills.pop(skillName, None)
			self._deactivatedSkills.pop(skillName, None)

			try:
				if not data['active']:
					if skillName in self.NEEDED_SKILLS:
						self.logInfo(f"Skill {skillName} marked as disabled but it shouldn't be")
						self.ProjectAlice.onStop()
						break

					self.logInfo(f'Skill {skillName} is disabled')

				if data['active']:
					self.checkSkillConditions(self._skillList[skillName]['installer'])

				skillInstance = self.instanciateSkill(skillName=skillName, reload=reload)
				if skillInstance:
					if skillName in self.NEEDED_SKILLS:
						skillInstance.required = True

					if data['active']:
						self._activeSkills[skillInstance.name] = skillInstance
					else:
						self._deactivatedSkills[skillName] = skillInstance
				else:
					self._failedSkills[skillName] = FailedAliceSkill(data['installer'])

			except SkillStartingFailed as e:
				self.logWarning(f'Failed loading skill: {e}')
				self._failedSkills[skillName] = FailedAliceSkill(data['installer'])
				continue
			except SkillNotConditionCompliant as e:
				self.logInfo(f'Skill {skillName} does not comply to "{e.condition}" condition, required "{e.conditionValue}"')
				self._failedSkills[skillName] = FailedAliceSkill(data['installer'])
				continue
			except Exception as e:
				self.logWarning(f'Something went wrong loading skill {skillName}: {e}')
				self._failedSkills[skillName] = FailedAliceSkill(data['installer'])
				continue


	# noinspection PyTypeChecker
	def instanciateSkill(self, skillName: str, skillResource: str = '', reload: bool = False) -> AliceSkill:
		instance: AliceSkill = None
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
		except Exception as e:
			self.logError(f"Couldn't instanciate skill {skillName}.{skillResource}: {e} {traceback.print_exc()}")

		return instance


	def onStop(self):
		super().onStop()

		for skillItem in self._activeSkills.values():
			skillItem.onStop()
			self.broadcast(method=constants.EVENT_SKILL_STOPPED, exceptions=[self.name], propagateToSkills=True, skill=self)


	def onQuarterHour(self):
		self.checkForSkillUpdates()


	def startAllSkills(self):
		supportedIntents = list()

		tmp = self._activeSkills.copy()
		for skillName in tmp:
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
			skillInstance = self.instanciateSkill(skillName=skillName)
			if skillInstance:
				self.activeSkills[skillName] = skillInstance
			else:
				return dict()
		elif skillName in self._failedSkills:
			skillInstance = self.instanciateSkill(skillName=skillName)
			if skillInstance:
				self.activeSkills[skillName] = skillInstance
			else:
				return dict()
		else:
			self.logWarning(f'Skill "{skillName}" is unknown')
			return dict()

		try:
			skillInstance.onStart()
			self.broadcast(method=constants.EVENT_SKILL_STARTED, exceptions=[self.name], propagateToSkills=True, skill=self)
		except SkillStartingFailed:
			self._failedSkills[skillName] = FailedAliceSkill(self._skillList[skillName]['installer'])
		except SkillStartDelayed:
			raise
		except Exception as e:
			self.logError(f'- Couldn\'t start skill "{skillName}". Error: {e}')

			try:
				self.deactivateSkill(skillName=skillName)
			except:
				self._activeSkills.pop(skillName, None)
				self._deactivatedSkills.pop(skillName, None)

			self._failedSkills[skillName] = FailedAliceSkill(self._skillList[skillName]['installer'])

		if skillInstance.widgets:
			self._widgets[skillName] = skillInstance.widgets

		if skillInstance.deviceTypes:
			self.DeviceManager.addDeviceTypes(deviceTypes=skillInstance.deviceTypes)

		return skillInstance.supportedIntents


	def isSkillActive(self, skillName: str) -> bool:
		if skillName in self._activeSkills:
			return self._activeSkills[skillName].active
		return False


	def getSkillInstance(self, skillName: str, silent: bool = False) -> Optional[AliceSkill]:
		if skillName in self._activeSkills:
			return self._activeSkills[skillName]
		else:
			if not silent:
				self.logWarning(f'Skill "{skillName}" is disabled, failed or does not exist in skills manager')

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
				self.logWarning(f'- Failed to broadcast event {method} to {skillName}: {e}')


	def deactivateSkill(self, skillName: str, persistent: bool = False):
		if skillName in self._activeSkills:
			skillInstance = self._activeSkills.pop(skillName)
			self._deactivatedSkills[skillName] = skillInstance
			skillInstance.onStop()
			self.broadcast(method=constants.EVENT_SKILL_STOPPED, exceptions=[self.name], propagateToSkills=True, skill=self)
			self._widgets.pop(skillName, None)
			self.DeviceManager.removeDeviceTypesForSkill(skillName=skillName)

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
	@IfSetting(settingName='stayCompletlyOffline', settingValue=False)
	def checkForSkillUpdates(self, skillToCheck: str = None) -> bool:
		self.logInfo('Checking for skill updates')
		updateCount = 0

		for skillName, data in self._skillList.items():
			if not data['active']:
				continue

			try:
				if skillToCheck and skillName != skillToCheck:
					continue

				remoteVersion = self.SkillStoreManager.getSkillUpdateVersion(skillName)
				localVersion = Version.fromString(self._skillList[skillName]['installer']['version'])
				if localVersion < remoteVersion:
					updateCount += 1
					self.logInfo(f'![yellow]({skillName}) - Version {self._skillList[skillName]["installer"]["version"]} < {str(remoteVersion)} in {self.ConfigManager.getAliceConfigByName("skillsUpdateChannel")}')

					if not self.ConfigManager.getAliceConfigByName('skillAutoUpdate'):
						if skillName in self._activeSkills:
							self._activeSkills[skillName].updateAvailable = True
					else:
						if not self.downloadInstallTicket(skillName):
							raise Exception
				else:
					self.logInfo(f'![green]({skillName}) - Version {self._skillList[skillName]["installer"]["version"]} in {self.ConfigManager.getAliceConfigByName("skillsUpdateChannel")}')

			except GithubNotFound:
				self.logInfo(f'![red](Skill **{skillName}**) is not available on Github. Deprecated or is it a dev skill?')

			except Exception as e:
				self.logError(f'Error checking updates for skill **{skillName}**: {e}')

		self.logInfo(f'Found {updateCount} skill update', plural='update')
		return updateCount > 0


	@Online(catchOnly=True)
	def _checkForSkillInstall(self):
		# Don't start the install timer from the main thread in case it's the first start
		if self._skillInstallThread:
			self.ThreadManager.newTimer(interval=10, func=self._checkForSkillInstall, autoStart=True)

		root = Path(self.Commons.rootDir(), constants.SKILL_INSTALL_TICKET_PATH)
		files = [f for f in root.iterdir() if f.suffix == '.install']

		if self._busyInstalling.isSet() or not files or self.ProjectAlice.restart or self.ProjectAlice.updating:
			return

		self.logInfo(f'Found {len(files)} install ticket', plural='ticket')
		self._busyInstalling.set()

		skillsToBoot = dict()
		try:
			skillsToBoot = self._installSkills(files)
		except Exception as e:
			self._logger.logError(f'Error installing skill: {e}')
		finally:
			self.MqttManager.mqttBroadcast(topic='hermes/leds/clear')

			if skillsToBoot:
				for skillName, info in skillsToBoot.items():
					self._initSkills(loadOnly=skillName, reload=info['update'])
					self.ConfigManager.loadCheckAndUpdateSkillConfigurations(skillToLoad=skillName)

					try:
						self._startSkill(skillName)
					except SkillStartDelayed:
						# The skill start was delayed
						pass

					if info['update']:
						self.allSkills[skillName].onSkillUpdated()
					else:
						self.allSkills[skillName].onSkillInstalled()

					if self.ProjectAlice.isBooted:
						self.allSkills[skillName].onBooted()

				self.AssistantManager.checkAssistant()

			self._busyInstalling.clear()


	def _installSkills(self, skills: list) -> dict:
		root = Path(self.Commons.rootDir(), constants.SKILL_INSTALL_TICKET_PATH)
		skillsToBoot = dict()
		self.MqttManager.mqttBroadcast(topic='hermes/leds/systemUpdate', payload={'sticky': True})
		for file in skills:
			skillName = Path(file).stem

			self.logInfo(f'Now taking care of skill {skillName}')
			res = root / file

			try:
				installFile = json.loads(res.read_text())

				skillName = installFile['name']
				path = Path(installFile['author'], skillName)

				if not skillName:
					self.logError('Skill name to install not found, aborting to avoid casualties!')
					continue

				directory = Path(self.Commons.rootDir()) / 'skills' / skillName

				if skillName in self._skillList:
					installedVersion = Version.fromString(self._skillList[skillName]['installer']['version'])
					remoteVersion = Version.fromString(installFile['version'])

					if installedVersion >= remoteVersion:
						self.logWarning(f'Skill "{skillName}" is already installed, skipping')
						self.Commons.runRootSystemCommand(['rm', res])
						continue
					else:
						self.logWarning(f'Skill "{skillName}" needs updating')
						updating = True
				else:
					updating = False

				self.checkSkillConditions(installFile)

				if skillName in self._activeSkills:
					try:
						self._activeSkills[skillName].onStop()
						self.broadcast(method=constants.EVENT_SKILL_STOPPED, exceptions=[self.name], propagateToSkills=True, skill=self)
					except Exception as e:
						self.logError(f'Error stopping "{skillName}" for update: {e}')
						raise

				gitCloner = GithubCloner(baseUrl=f'{constants.GITHUB_URL}/skill_{skillName}.git', path=path, dest=directory)

				try:
					gitCloner.clone(skillName=skillName)
					self.logInfo('Skill successfully downloaded')
					self._installSkill(res)
					skillsToBoot[skillName] = {
						'update': updating
					}
				except (GithubTokenFailed, GithubRateLimit):
					self.logError('Failed cloning skill')
					raise
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
				'installer': installFile
			}

			os.unlink(str(res))
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
				if conditionValue and self.ConfigManager.getAliceConfigByName('stayCompletlyOffline') \
						or not conditionValue and not self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
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
			self.logWarning(f'Intent configuration failed: {e} {traceback.print_exc()}')


	def isIntentInUse(self, intent: Intent, filtered: list) -> bool:
		skills = self.allWorkingSkills
		return any(intent in skill.supportedIntents for name, skill in skills.items() if name not in filtered)


	def removeSkill(self, skillName: str):
		if skillName not in self.allSkills:
			return

		self.broadcast(method=constants.EVENT_SKILL_DELETED, exceptions=[self.name], propagateToSkills=True, skill=skillName)

		if skillName in self._activeSkills:
			self._activeSkills[skillName].onStop()
			self.broadcast(method=constants.EVENT_SKILL_STOPPED, exceptions=[self.name], propagateToSkills=True, skill=self)

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

		self._initSkills(loadOnly=skillName, reload=True)

		self.AssistantManager.checkAssistant()

		self._startSkill(skillName=skillName)


	def allScenarioNodes(self) -> Dict[str, tuple]:
		ret = dict()
		for skillName, skillInstance in self._activeSkills.items():
			if not skillInstance.hasScenarioNodes():
				continue

			ret[skillName] = (skillInstance.scenarioNodeName, skillInstance.scenarioNodeVersion, skillInstance.getResource('scenarioNodes'))

		return ret


	def wipeSkills(self, addDefaults: bool = True):
		shutil.rmtree(Path(self.Commons.rootDir(), 'skills'))
		Path(self.Commons.rootDir(), 'skills').mkdir()

		if addDefaults:
			tickets = [
				'https://skills.projectalice.ch/AliceCore',
				'https://skills.projectalice.ch/ContextSensitive',
				'https://skills.projectalice.ch/RedQueen',
				'https://skills.projectalice.ch/Telemetry',
				'https://skills.projectalice.ch/DateDayTimeYear'
			]
			for link in tickets:
				self.downloadInstallTicket(link.rsplit('/')[-1])

		self._activeSkills = dict()
		self._deactivatedSkills = dict()
		self._failedSkills = dict()
		self._loadSkills()


	def createNewSkill(self, skillDefinition: dict) -> bool:
		try:
			self.logInfo(f'Creating new skill "{skillDefinition["name"]}"')

			rootDir = Path(self.Commons.rootDir()) / 'skills'
			skillTemplateDir = rootDir / 'skill_DefaultTemplate'

			if skillTemplateDir.exists():
				shutil.rmtree(skillTemplateDir)

			self.Commons.runSystemCommand(['git', '-C', str(rootDir), 'clone', f'{constants.GITHUB_URL}/skill_DefaultTemplate.git'])

			skillName = skillDefinition['name'][0].upper() + skillDefinition['name'][1:]
			skillDir = rootDir / skillName

			skillTemplateDir.rename(skillDir)

			installFile = skillDir / f'{skillDefinition["name"]}.install'
			Path(skillDir, 'DefaultTemplate.install').rename(installFile)
			supportedLanguages = [
				'en'
			]
			if skillDefinition['fr'] == 'yes':
				supportedLanguages.append('fr')
			if skillDefinition['de'] == 'yes':
				supportedLanguages.append('de')
			if skillDefinition['it'] == 'yes':
				supportedLanguages.append('it')

			conditions = {
				'lang': supportedLanguages
			}

			if skillDefinition['conditionOnline']:
				conditions['online'] = True

			if skillDefinition['conditionASRArbitrary']:
				conditions['asrArbitraryCapture'] = True

			if skillDefinition['conditionSkill']:
				conditions['skill'] = [skill.strip() for skill in skillDefinition['conditionSkill'].split(',')]

			if skillDefinition['conditionNotSkill']:
				conditions['notSkill'] = [skill.strip() for skill in skillDefinition['conditionNotSkill'].split(',')]

			if skillDefinition['conditionActiveManager']:
				conditions['activeManager'] = [manager.strip() for manager in skillDefinition['conditionActiveManager'].split(',')]

			installContent = {
				'name'              : skillName,
				'version'           : '0.0.1',
				'icon'              : 'fab fa-battle-net',
				'category'          : 'undefined',
				'author'            : self.ConfigManager.getAliceConfigByName('githubUsername'),
				'maintainers'       : [],
				'desc'              : skillDefinition['description'].capitalize(),
				'aliceMinVersion'   : constants.VERSION,
				'systemRequirements': [req.strip() for req in skillDefinition['sysreq'].split(',')],
				'pipRequirements'   : [req.strip() for req in skillDefinition['pipreq'].split(',')],
				'conditions'        : conditions
			}

			# Install file
			with installFile.open('w') as fp:
				fp.write(json.dumps(installContent, indent=4))

			# Dialog templates and talks
			dialogTemplateTemplate = skillDir / 'dialogTemplate/default.json'
			with dialogTemplateTemplate.open() as fp:
				dialogTemplate = json.load(fp)
				dialogTemplate['skill'] = skillName
				dialogTemplate['description'] = skillDefinition['description'].capitalize()

			for lang in supportedLanguages:
				with Path(skillDir, f'dialogTemplate/{lang}.json').open('w+') as fp:
					fp.write(json.dumps(dialogTemplate, indent=4))

				with Path(skillDir, f'talks/{lang}.json').open('w+') as fp:
					fp.write(json.dumps(dict()))

			dialogTemplateTemplate.unlink()

			# Widgets
			if skillDefinition['widgets']:
				widgetRootDir = skillDir / 'widgets'
				css = widgetRootDir / 'css/widget.css'
				js = widgetRootDir / 'js/widget.js'
				lang = widgetRootDir / 'lang/widget.lang.json'
				html = widgetRootDir / 'templates/widget.html'
				python = widgetRootDir / 'widget.py'

				for widget in skillDefinition['widgets'].split(','):
					widgetName = widget.strip()
					widgetName = widgetName[0].upper() + widgetName[1:]

					content = css.read_text().replace('%widgetname%', widgetName)
					with Path(widgetRootDir, f'css/{widgetName}.css').open('w+') as fp:
						fp.write(content)

					shutil.copy(str(js), str(js).replace('widget.js', f'{widgetName}.js'))
					shutil.copy(str(lang), str(lang).replace('widget.lang.json', f'{widgetName}.lang.json'))

					content = html.read_text().replace('%widgetname%', widgetName)
					with Path(widgetRootDir, f'templates/{widgetName}.html').open('w+') as fp:
						fp.write(content)

					content = python.read_text().replace('Template(Widget)', f'{widgetName}(Widget)')
					with Path(widgetRootDir, f'{widgetName}.py').open('w+') as fp:
						fp.write(content)

				css.unlink()
				js.unlink()
				lang.unlink()
				html.unlink()
				python.unlink()

			else:
				shutil.rmtree(str(Path(skillDir, 'widgets')))

			languages = ''
			for lang in supportedLanguages:
				languages += f'    {lang}\n'

			# Readme file
			content = Path(skillDir, 'README.md').read_text().replace('%skillname%', skillName) \
				.replace('%author%', self.ConfigManager.getAliceConfigByName('githubUsername')) \
				.replace('%minVersion%', constants.VERSION) \
				.replace('%description%', skillDefinition['description'].capitalize()) \
				.replace('%languages%', languages)

			with Path(skillDir, 'README.md').open('w') as fp:
				fp.write(content)

			# Main class
			classFile = skillDir / f'{skillDefinition["name"]}.py'
			Path(skillDir, 'DefaultTemplate.py').rename(classFile)

			content = classFile.read_text().replace('%skillname%', skillName) \
				.replace('%author%', self.ConfigManager.getAliceConfigByName('githubUsername')) \
				.replace('%description%', skillDefinition['description'].capitalize())

			with classFile.open('w') as fp:
				fp.write(content)

			self.logInfo(f'Created "{skillDefinition["name"]}" skill')

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
			self.Commons.runSystemCommand(['git', '-C', str(localDirectory), 'commit', '-m', '"Initial upload"'])
			self.Commons.runSystemCommand(['git', '-C', str(localDirectory), 'push', '--set-upstream', 'origin', 'master'])

			url = f'https://github.com/{self.ConfigManager.getAliceConfigByName("githubUsername")}/skill_{skillName}.git'
			self.logInfo(f'Skill uploaded! You can find it on {url}')
			return True
		except Exception as e:
			self.logWarning(f'Something went wrong uploading skill to Github: {e}')
			return False


	def downloadInstallTicket(self, skillName: str) -> bool:
		try:
			tmpFile = Path(self.Commons.rootDir(), f'system/skillInstallTickets/{skillName}.install')
			if not self.Commons.downloadFile(
					url=f'{constants.GITHUB_RAW_URL}/skill_{skillName}/{self.SkillStoreManager.getSkillUpdateTag(skillName)}/{skillName}.install',
					dest=str(tmpFile.with_suffix('.tmp'))
			):
				raise Exception

			shutil.move(tmpFile.with_suffix('.tmp'), tmpFile)
			return True
		except Exception as e:
			self.logError(f'Error downloading install ticket for skill "{skillName}": {e}')
			return False
