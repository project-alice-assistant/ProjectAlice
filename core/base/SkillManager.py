import importlib
import json
from pathlib import Path
from typing import Dict, Optional

import os
import requests
import shutil

from core.ProjectAliceExceptions import GithubNotFound, GithubRateLimit, GithubTokenFailed, SkillNotConditionCompliant, SkillStartDelayed, SkillStartingFailed
from core.base.SuperManager import SuperManager
from core.base.model import Intent
from core.base.model.AliceSkill import AliceSkill
from core.base.model.GithubCloner import GithubCloner
from core.base.model.Manager import Manager
from core.base.model.Version import Version
from core.commons import constants


class SkillManager(Manager):

	NEEDED_SKILLS = [
		'AliceCore',
		'ContextSensitive',
		'RedQueen'
	]

	GITHUB_BARE_BASE_URL = 'https://raw.githubusercontent.com/project-alice-assistant/ProjectAliceSkills/master/PublishedSkills'
	GITHUB_API_BASE_URL = 'repositories/193512918/contents/PublishedSkills'

	GITHUB_BASE_URL = 'https://github.com/project-alice-assistant/skill_{}.git'

	DATABASE = {
		'widgets': [
			'parent TEXT NOT NULL UNIQUE',
			'name TEXT NOT NULL UNIQUE',
			'posx INTEGER NOT NULL',
			'posy INTEGER NOT NULL',
			'state TEXT NOT NULL',
			'options TEXT NOT NULL',
			'zindex INTEGER'
		]
	}

	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)

		self._busyInstalling = None

		self._skillInstallThread = None
		self._supportedIntents = list()
		self._allSkills = dict()
		self._activeSkills = dict()
		self._failedSkills = dict()
		self._deactivatedSkills = dict()
		self._widgets = dict()


	def onStart(self):
		super().onStart()

		self._busyInstalling = self.ThreadManager.newEvent('skillInstallation')

		# If it's the first time we start, don't delay skill install and do it on main thread
		if not self.ConfigManager.getAliceConfigByName('skills'):
			self.logInfo('Looks like a fresh install or skills were nuked. Let\'s install the basic skills!')
			self._checkForSkillInstall()

		self._skillInstallThread = self.ThreadManager.newThread(name='SkillInstallThread', target=self._checkForSkillInstall, autostart=False)

		self._activeSkills = self._loadSkillList()
		self._allSkills = {**self._activeSkills, **self._deactivatedSkills, **self._failedSkills}

		for skillName in self._deactivatedSkills:
			self.configureSkillIntents(skillName=skillName, state=False)

		self.checkForSkillUpdates()
		self.startAllSkills()


	def onSnipsAssistantDownloaded(self, **kwargs):
		self.MqttManager.mqttBroadcast(topic='hermes/leds/clear')

		argv = kwargs.get('skillsInfos', dict())
		if not argv:
			return

		for skillName, skill in argv.items():
			try:
				self._startSkill(skillInstance=self._activeSkills[skillName])
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
	def widgets(self) -> dict:
		return self._widgets


	@property
	def supportedIntents(self) -> list:
		return self._supportedIntents


	@property
	def neededSkills(self) -> list:
		return self.NEEDED_SKILLS


	@property
	def activeSkills(self) -> dict:
		return self._activeSkills


	@property
	def deactivatedSkills(self) -> dict:
		return self._deactivatedSkills


	@property
	def allSkills(self) -> dict:
		return self._allSkills


	@property
	def failedSkills(self) -> dict:
		return self._failedSkills


	def onBooted(self):
		self.skillBroadcast(constants.EVENT_BOOTED)
		self._skillInstallThread.start()


	def _loadSkillList(self, skillToLoad: str = '', isUpdate: bool = False) -> dict:
		skills = self._allSkills.copy() if skillToLoad else dict()

		availableSkills = self.ConfigManager.skillsConfigurations
		availableSkills = dict(sorted(availableSkills.items()))

		for skillName, skill in availableSkills.items():
			if skillToLoad and skillName != skillToLoad:
				continue

			try:
				if not skill['active']:
					if skillName in self.NEEDED_SKILLS:
						self.logInfo(f"Skill {skillName} marked as disable but it shouldn't be")
						self.ProjectAlice.onStop()
						break
					else:
						self.logInfo(f'Skill {skillName} is disabled')

						skillInstance = self.importFromSkill(skillName=skillName, isUpdate=False)
						if skillInstance:
							skillInstance.active = False

							if skillName in self.NEEDED_SKILLS:
								skillInstance.required = True

							self._deactivatedSkills[skillInstance.name] = skillInstance
						continue

				self.checkSkillConditions(skillName, skill['conditions'], availableSkills)

				name = self.Commons.toCamelCase(skillName) if ' ' in skillName else skillName

				skillInstance = self.importFromSkill(skillName=name, isUpdate=isUpdate)

				if skillInstance:

					if skillName in self.NEEDED_SKILLS:
						skillInstance.required = True

					skills[skillInstance.name] = skillInstance
				else:
					self._failedSkills[name] = None

			except SkillStartingFailed as e:
				self.logWarning(f'Failed loading skill: {e}')
				continue
			except SkillNotConditionCompliant as e:
				self.logInfo(f'Skill {skillName} does not comply to "{e.condition}" condition, required "{e.conditionValue}"')
				continue
			except Exception as e:
				self.logWarning(f'Something went wrong loading skill {skillName}: {e}')
				continue

		return dict(sorted(skills.items()))


	# noinspection PyTypeChecker
	def importFromSkill(self, skillName: str, skillResource: str = '', isUpdate: bool = False) -> AliceSkill:
		instance: AliceSkill = None

		skillResource = skillResource or skillName

		try:
			skillImport = importlib.import_module(f'skills.{skillName}.{skillResource}')

			if isUpdate:
				skillImport = importlib.reload(skillImport)

			klass = getattr(skillImport, skillName)
			instance: AliceSkill = klass()
		except ImportError as e:
			self.logError(f"Couldn't import skill {skillName}.{skillResource}: {e}")
		except AttributeError as e:
			self.logError(f"Couldn't find main class for skill {skillName}.{skillResource}: {e}")
		except Exception as e:
			self.logError(f"Couldn't instantiate skill {skillName}.{skillResource}: {e}")

		return instance


	def onStop(self):
		super().onStop()

		for skillItem in self._activeSkills.values():
			skillItem.onStop()
			self.logInfo(f'- {skillItem.name} stopped!')


	def onFullHour(self):
		self.checkForSkillUpdates()


	def startAllSkills(self):
		supportedIntents = list()

		tmp = self._activeSkills.copy()
		for skillName, skillItem in tmp.items():
			try:
				supportedIntents += self._startSkill(skillItem)
			except SkillStartingFailed:
				continue
			except SkillStartDelayed:
				self.logInfo(f'Skill {skillName} start is delayed')

		supportedIntents = list(set(supportedIntents))

		self._supportedIntents = supportedIntents

		self.logInfo(f'All skills started. {len(supportedIntents)} intents supported')


	def _startSkill(self, skillInstance: AliceSkill) -> dict:
		try:
			name = skillInstance.name
			skillInstance.onStart()
			intents = skillInstance.supportedIntents

			if skillInstance.widgets:
				self._widgets[name] = skillInstance.widgets

			if intents:
				self.logInfo('- Started!')
				return intents
		except (SkillStartingFailed, SkillStartDelayed):
			raise
		except Exception as e:
			# noinspection PyUnboundLocalVariable
			self.logError(f'- Couldn\'t start skill {name or "undefined"}. Did you forget to return the intents in onStart()? Error: {e}')

		return dict()


	def isSkillActive(self, skillName: str) -> bool:
		return skillName in self._activeSkills


	def getSkillInstance(self, skillName: str, silent: bool = False) -> Optional[AliceSkill]:
		if skillName in self._allSkills:
			return self._allSkills[skillName]
		else:
			if not silent:
				self.logWarning(f'Skill "{skillName}" is disabled or does not exist in skills manager')

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

		for skillItem in self._activeSkills.values():

			if filterOut and skillItem.name in filterOut:
				continue

			try:
				func = getattr(skillItem, method, None)
				if func:
					func(**kwargs)

				func = getattr(skillItem, 'onEvent', None)
				if func:
					func(event=method, **kwargs)

			except TypeError as e:
				self.logWarning(f'- Failed to broadcast event {method} to {skillItem.name}: {e}')


	def deactivateSkill(self, skillName: str, persistent: bool = False):
		if skillName in self._activeSkills:
			self._activeSkills[skillName].active = False
			self.ConfigManager.deactivateSkill(skillName, persistent)
			self.configureSkillIntents(skillName=skillName, state=False)
			self._deactivatedSkills[skillName] = self._activeSkills.pop(skillName)


	def activateSkill(self, skillName: str, persistent: bool = False):
		if skillName in self._deactivatedSkills:
			self.ConfigManager.activateSkill(skillName, persistent)
			self.configureSkillIntents(skillName=skillName, state=True)
			self._activeSkills[skillName] = self._deactivatedSkills.pop(skillName)
			self._activeSkills[skillName].active = True
			self._activeSkills[skillName].onStart()


	def checkForSkillUpdates(self, skillToCheck: str = None) -> bool:
		if self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
			return False

		self.logInfo('Checking for skill updates')
		if not self.InternetManager.online:
			self.logInfo('Not connected...')
			return False

		availableSkills = self.ConfigManager.skillsConfigurations
		updateCount = 0

		for skillName in self._allSkills:
			try:
				if skillToCheck and skillName != skillToCheck:
					continue

				remoteVersion = self.SkillStoreManager.getSkillUpdateVersion(skillName)
				localVersion = Version.fromString(availableSkills[skillName]['version'])
				if localVersion < remoteVersion:
					updateCount += 1
					self.logInfo(f'❌ {skillName} - Version {availableSkills[skillName]["version"]} < {str(remoteVersion)} in {self.ConfigManager.getAliceConfigByName("skillsUpdateChannel")}')

					if not self.ConfigManager.getAliceConfigByName('skillAutoUpdate'):
						if skillName in self._activeSkills:
							self._activeSkills[skillName].updateAvailable = True
						elif skillName in self._deactivatedSkills:
							self._deactivatedSkills[skillName].updateAvailable = True
					else:

						req = requests.get(f'https://raw.githubusercontent.com/project-alice-assistant/skill_{skillName}/{self.SkillStoreManager.getSkillUpdateTag(skillName)}/{skillName}.install')

						if req.status_code == 404:
							raise GithubNotFound

						remoteFile = req.json()
						if not remoteFile:
							raise Exception

						skillFile = Path(self.Commons.rootDir(), constants.SKILL_INSTALL_TICKET_PATH, skillName + '.install')
						skillFile.write_text(json.dumps(remoteFile))
						if skillName in self._failedSkills:
							del self._failedSkills[skillName]
				else:
					self.logInfo(f'✔ {skillName} - Version {availableSkills[skillName]["version"]} in {self.ConfigManager.getAliceConfigByName("skillsUpdateChannel")}')

			except GithubNotFound:
				self.logInfo(f'❓ Skill "{skillName}" is not available on Github. Deprecated or is it a dev skill?')

			except Exception as e:
				self.logError(f'❗ Error checking updates for skill "{skillName}": {e}')

		self.logInfo(f'Found {updateCount} skill update(s)')
		return updateCount > 0


	def _checkForSkillInstall(self):
		# Don't start the install timer from the main thread in case it's the first start
		if self._skillInstallThread is not None:
			self.ThreadManager.newTimer(interval=10, func=self._checkForSkillInstall, autoStart=True)

		root = Path(self.Commons.rootDir(), constants.SKILL_INSTALL_TICKET_PATH)
		files = [f for f in root.iterdir() if f.suffix == '.install']

		if self._busyInstalling.isSet() or \
				not self.InternetManager.online or \
				not files or \
				self.ThreadManager.getEvent('SnipsAssistantDownload').isSet():
			return

		if files:
			self.logInfo(f'Found {len(files)} install ticket(s)')
			self._busyInstalling.set()

			skillsToBoot = dict()
			try:
				skillsToBoot = self._installSkills(files)
			except Exception as e:
				self._logger.error(f'Error installing skill: {e}')
			finally:
				self.MqttManager.mqttBroadcast(topic='hermes/leds/clear')

				if skillsToBoot:
					for skillName, info in skillsToBoot.items():
						self._activeSkills = self._loadSkillList(skillToLoad=skillName, isUpdate=info['update'])
						self._allSkills = {**self._allSkills, **self._activeSkills}

						try:
							self.LanguageManager.loadStrings(skillToLoad=skillName)
							self.TalkManager.loadTalks(skillToLoad=skillName)
						except:
							pass

					self.NluManager.afterNewSkillInstall()

				self._busyInstalling.clear()


	def _installSkills(self, skills: list) -> dict:
		root = Path(self.Commons.rootDir(), constants.SKILL_INSTALL_TICKET_PATH)
		availableSkills = self.ConfigManager.skillsConfigurations
		skillsToBoot = dict()
		self.MqttManager.mqttBroadcast(topic='hermes/leds/systemUpdate', payload={'sticky': True})
		for file in skills:
			skillName = Path(file).with_suffix('')

			self.logInfo(f'Now taking care of skill {skillName.stem}')
			res = root / file

			try:
				updating = False

				installFile = json.loads(res.read_text())

				skillName = installFile['name']
				path = Path(installFile['author'], skillName)

				if not skillName:
					self.logError('Skill name to install not found, aborting to avoid casualties!')
					continue

				directory = Path(self.Commons.rootDir()) / 'skills' / skillName

				conditions = {
					'aliceMinVersion': installFile['aliceMinVersion'],
					**installFile.get('conditions', dict())
				}

				self.checkSkillConditions(skillName, conditions, availableSkills)

				if skillName in availableSkills:
					installedVersion = Version.fromString(availableSkills[skillName]['version'])
					remoteVersion = Version.fromString(installFile['version'])
					localVersionIsLatest: bool = \
						directory.is_dir() and \
						'version' in availableSkills[skillName] and \
						installedVersion >= remoteVersion

					if localVersionIsLatest:
						self.logWarning(f'Skill "{skillName}" is already installed, skipping')
						self.Commons.runRootSystemCommand(['rm', res])
						continue
					else:
						self.logWarning(f'Skill "{skillName}" needs updating')
						updating = True

				if skillName in self._activeSkills:
					try:
						self._activeSkills[skillName].onStop()
					except Exception as e:
						self.logError(f'Error stopping "{skillName}" for update: {e}')
						raise

				gitCloner = GithubCloner(baseUrl=self.GITHUB_BASE_URL.format(skillName), path=path, dest=directory)

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

			except Exception as e:
				self.logError(f'Failed installing skill "{skillName}": {e}')
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
				self.Commons.runSystemCommand(['./venv/bin/pip3', 'install', requirement])

			for requirement in sysReqs:
				self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', requirement])

			if scriptReq:
				self.Commons.runRootSystemCommand(['chmod', '+x', str(directory / scriptReq)])
				self.Commons.runRootSystemCommand([str(directory / scriptReq)])

			node = {
				'active'    : True,
				'version'   : installFile['version'],
				'author'    : installFile['author'],
				'conditions': installFile['conditions']
			}

			os.unlink(str(res))
			self.ConfigManager.addSkillToAliceConfig(installFile['name'], node)
		except Exception:
			raise


	def checkSkillConditions(self, skillName: str, conditions: dict, availableSkills: dict) -> bool:

		notCompliant = 'Skill is not compliant'

		if 'aliceMinVersion' in conditions and \
				Version.fromString(conditions['aliceMinVersion']) > Version.fromString(constants.VERSION):
			raise SkillNotConditionCompliant(message=notCompliant, skillName=skillName, condition='Alice minimum version', conditionValue=conditions['aliceMinVersion'])

		for conditionName, conditionValue in conditions.items():
			if conditionName == 'lang' and self.LanguageManager.activeLanguage not in conditionValue:
				raise SkillNotConditionCompliant(message=notCompliant, skillName=skillName, condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'online':
				if conditionValue and self.ConfigManager.getAliceConfigByName('stayCompletlyOffline') \
						or not conditionValue and not self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
					raise SkillNotConditionCompliant(message=notCompliant, skillName=skillName, condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'skill':
				for requiredSkill in conditionValue:
					if requiredSkill['name'] in availableSkills and not availableSkills[requiredSkill['name']]['active']:
						raise SkillNotConditionCompliant(message=notCompliant, skillName=skillName, condition=conditionName, conditionValue=conditionValue)
					elif requiredSkill['name'] not in availableSkills:
						self.logInfo(f'Skill {skillName} has another skill as dependency, adding download')
						if not self.Commons.downloadFile(requiredSkill['url'], Path(self.Commons.rootDir(), f"system/skillInstallTickets/{requiredSkill['name']}.install")):
							raise SkillNotConditionCompliant(message=notCompliant, skillName=skillName, condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'notSkill':
				for excludedSkill in conditionValue:
					author, name = excludedSkill.split('/')
					if name in availableSkills and availableSkills[name]['author'] == author and availableSkills[name]['active']:
						raise SkillNotConditionCompliant(message=notCompliant, skillName=skillName, condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'asrArbitraryCapture':
				if conditionValue and not self.ASRManager.asr.capableOfArbitraryCapture:
					raise SkillNotConditionCompliant(message=notCompliant, skillName=skillName, condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'activeManager':
				for manager in conditionValue:
					if not manager: continue

					man = SuperManager.getInstance().getManager(manager)
					if not man or not man.isActive:
						raise SkillNotConditionCompliant(message=notCompliant, skillName=skillName, condition=conditionName, conditionValue=conditionValue)

		return True


	def configureSkillIntents(self, skillName: str, state: bool):
		try:
			skill = self._activeSkills.get(skillName, self._deactivatedSkills.get(skillName))
			confs = [{
				'intentId': intent.justTopic if hasattr(intent, 'justTopic') else intent,
				'enable': state
			} for intent in skill.supportedIntents if not self.isIntentInUse(intent=intent, filtered=[skillName])]

			self.MqttManager.configureIntents(confs)
		except Exception as e:
			self.logWarning(f'Intent configuration failed: {e}')


	def isIntentInUse(self, intent: Intent, filtered: list) -> bool:
		return any(intent in skill.supportedIntents
		           for name, skill in self._activeSkills.items() if name not in filtered)


	def removeSkill(self, skillName: str):
		if skillName not in self._allSkills:
			return

		self.configureSkillIntents(skillName, False)
		self.ConfigManager.removeSkill(skillName)

		self._activeSkills.pop(skillName, None)
		self._deactivatedSkills.pop(skillName, None)
		self._allSkills.pop(skillName, None)

		self.NluManager.cleanCache(skillName)

		shutil.rmtree(Path(self.Commons.rootDir(), 'skills', skillName))


	def reloadSkill(self, skillName: str):
		if skillName not in self._allSkills:
			return

		try:
			self._allSkills[skillName].onStop()
		except:
			# Do nothing, it's maybe because the skill crashed while running
			pass

		self._loadSkillList(skillToLoad=skillName, isUpdate=True)
		self._startSkill(self._allSkills[skillName])


	def allScenarioNodes(self, includeInactive: bool = False) -> Dict[str, tuple]:
		skills = self._activeSkills if not includeInactive else self._allSkills

		ret = dict()
		for skill in skills.values():
			if not skill.hasScenarioNodes():
				continue

			ret[skill.name] = (skill.scenarioNodeName, skill.scenarioNodeVersion, Path(skill.getCurrentDir(), 'scenarioNodes'))

		return ret


	def createNewSkill(self, skillDefinition: dict) -> bool:
		try:
			self.logInfo(f'Creating new skill "{skillDefinition["name"]}"')

			rootDir = Path(self.Commons.rootDir()) / 'skills'
			skillTemplateDir = rootDir / 'skill_DefaultTemplate'

			if skillTemplateDir.exists():
				self.Commons.runSystemCommand(['git', '-C', str(rootDir), 'stash'])
				self.Commons.runSystemCommand(['git', '-C', str(rootDir), 'clear', '-dfx'])
				self.Commons.runSystemCommand(['git', '-C', str(rootDir), 'pull'])
			else:
				self.Commons.runSystemCommand(['git', '-C', str(rootDir), 'clone', 'https://github.com/project-alice-assistant/skill_DefaultTemplate.git'])

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

			conditions = {
				'lang': supportedLanguages
			}

			readmeConditions = ''
			readmeReqs = ''
			readmeWidgets = ''

			if skillDefinition['conditionOnline']:
				conditions['online'] = True
				readmeConditions += '    Online\n'

			if skillDefinition['conditionASRArbitrary']:
				conditions['asrArbitraryCapture'] = True
				readmeConditions += '    Arbitrary capture\n'

			if skillDefinition['conditionSkill']:
				conditions['skill'] = [skill.strip() for skill in skillDefinition['conditionSkill'].split(',')]
				readmeConditions += f'    Required skills: {str(conditions["skill"])}\n'

			if skillDefinition['conditionNotSkill']:
				conditions['notSkill'] = [skill.strip() for skill in skillDefinition['conditionNotSkill'].split(',')]
				readmeConditions += f'    Conflicting skills: {str(conditions["notSkill"])}\n'

			if skillDefinition['conditionActiveManager']:
				conditions['activeManager'] = [manager.strip() for manager in skillDefinition['conditionActiveManager'].split(',')]
				readmeConditions += f'    Active managers: {str(conditions["activeManager"])}\n'

			installContent = {
				'name'              : skillName,
				'version'           : '0.0.1',
				'author'            : self.ConfigManager.getAliceConfigByName('githubUsername'),
				'maintainers'       : [],
				'desc'              : skillDefinition['description'].capitalize(),
				'aliceMinVersion'   : constants.VERSION,
				'systemRequirements': [req.strip() for req in skillDefinition['sysreq'].split(',')],
				'pipRequirements'   : [req.strip() for req in skillDefinition['pipreq'].split(',')],
				'conditions'        : conditions
			}

			readmeReqs += f'    PIP: {str(installContent["pipRequirements"])}\n'
			readmeReqs += f'    System: {str(installContent["systemRequirements"])}\n'

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
				lang = widgetRootDir / 'lang/widget.json'
				html = widgetRootDir / 'templates/widget.html'
				python = widgetRootDir / 'widget.py'

				for widget in skillDefinition['widgets'].split(','):
					widgetName = widget.strip()
					widgetName = widgetName[0].upper() + widgetName[1:]
					readmeWidgets += f'    {widgetName}\n'

					with css.open() as fp:
						content = fp.read().replace('%widgetname%', widgetName)

					with Path(widgetRootDir, f'css/{widgetName}.css').open('w+') as fp:
						fp.write(content)

					shutil.copy(str(js), str(js).replace('widget.js', f'{widgetName}.js'))
					shutil.copy(str(lang), str(lang).replace('widget.json', f'{widgetName}.json'))

					with html.open() as fp:
						content = fp.read().replace('%widgetname%', widgetName)

					with Path(widgetRootDir, f'templates/{widgetName}.html').open('w+') as fp:
						fp.write(content)

					with python.open() as fp:
						content = fp.read().replace('Template(Widget)', f'{widgetName}(Widget)')

					with Path(widgetRootDir, f'{widgetName}.py').open('w+') as fp:
						fp.write(content)

				css.unlink()
				js.unlink()
				lang.unlink()
				html.unlink()
				python.unlink()

			else:
				shutil.rmtree(str(Path(skillDir, 'widgets')))

			# Readme file
			# For some reason r+ mode appends at the end instead of overwritting
			with Path(skillDir, 'README.md').open() as fp:
				content = fp.read().replace('%skillname%', skillName) \
					.replace('%author%', self.ConfigManager.getAliceConfigByName('githubUsername')) \
					.replace('%description%', skillDefinition['description'].capitalize()) \
					.replace('%conditions%', readmeConditions) \
					.replace('%requirements%', readmeReqs) \
					.replace('%widgets%', readmeWidgets)

			with Path(skillDir, 'README.md').open('w') as fp:
				fp.write(content)

			self.logInfo(f'Created "{skillDefinition["name"]}" skill')

			return True
		except Exception as e:
			self.logError(f'Error creating new skill: {e}')
			return False
