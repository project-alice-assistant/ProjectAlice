import importlib
import json
import subprocess
from pathlib import Path
from typing import Optional

import requests
import shutil

from core.ProjectAliceExceptions import GithubNotFound, GithubRateLimit, GithubTokenFailed, ModuleNotConditionCompliant, ModuleStartDelayed, ModuleStartingFailed
from core.base.SuperManager import SuperManager
from core.base.model import Intent
from core.base.model.GithubCloner import GithubCloner
from core.base.model.Manager import Manager
from core.base.model.Module import Module
from core.base.model.Version import Version
from core.commons import constants


class SkillManager(Manager):

	NAME = 'SkillManager'

	NEEDED_MODULES = [
		'AliceCore',
		'ContextSensitive',
		'RedQueen'
	]

	GITHUB_BARE_BASE_URL = 'https://raw.githubusercontent.com/project-alice-assistant/ProjectAliceModules/master/PublishedModules'
	GITHUB_API_BASE_URL = 'repositories/193512918/contents/PublishedModules'

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
		super().__init__(self.NAME, self.DATABASE)

		self._busyInstalling        = None

		self._moduleInstallThread   = None
		self._supportedIntents      = list()
		self._allModules            = dict()
		self._activeModules         = dict()
		self._failedModules         = dict()
		self._deactivatedModules    = dict()
		self._widgets               = dict()


	def onStart(self):
		super().onStart()

		self._busyInstalling = self.ThreadManager.newEvent('moduleInstallation')
		self._moduleInstallThread = self.ThreadManager.newThread(name='ModuleInstallThread', target=self._checkForModuleInstall, autostart=False)

		self._activeModules = self._loadModuleList()
		self._allModules = {**self._activeModules, **self._deactivatedModules, **self._failedModules}

		for skillName in self._deactivatedModules:
			self.configureModuleIntents(skillName=skillName, state=False)

		self.checkForModuleUpdates()
		self.startAllModules()


	def onSnipsAssistantDownloaded(self, **kwargs):
		argv = kwargs.get('modulesInfos', dict())
		if not argv:
			return

		for skillName, module in argv.items():
			try:
				self._startModule(moduleInstance=self._activeModules[skillName])
			except ModuleStartDelayed:
				self.logInfo(f'Module "{skillName}" start is delayed')
			except KeyError as e:
				self.logError(f'Module "{skillName} not found, skipping: {e}')
				continue

			self._activeModules[skillName].onBooted()

			self.broadcast(
				method='onModuleUpdated' if module['update'] else 'onModuleInstalled',
				exceptions=[constants.DUMMY],
				module=skillName
			)


	def onModuleInstalled(self):
		pass


	@property
	def widgets(self) -> dict:
		return self._widgets


	@property
	def supportedIntents(self) -> list:
		return self._supportedIntents


	@property
	def neededModules(self) -> list:
		return self.NEEDED_MODULES


	@property
	def activeModules(self) -> dict:
		return self._activeModules


	@property
	def deactivatedModules(self) -> dict:
		return self._deactivatedModules


	@property
	def allModules(self) -> dict:
		return self._allModules


	@property
	def failedModules(self) -> dict:
		return self._failedModules


	def onBooted(self):
		self.skillBroadcast('onBooted')
		self._moduleInstallThread.start()


	def _loadModuleList(self, moduleToLoad: str = '', isUpdate: bool = False) -> dict:
		modules = self._allModules.copy() if moduleToLoad else dict()

		availableModules = self.ConfigManager.modulesConfigurations
		availableModules = dict(sorted(availableModules.items()))

		for skillName, module in availableModules.items():
			if moduleToLoad and skillName != moduleToLoad:
				continue

			try:
				if not module['active']:
					if skillName in self.NEEDED_MODULES:
						self.logInfo(f"Module {skillName} marked as disable but it shouldn't be")
						self.ProjectAlice.onStop()
						break
					else:
						self.logInfo(f'Module {skillName} is disabled')

						moduleInstance = self.importFromModule(skillName=skillName, isUpdate=False)
						if moduleInstance:
							moduleInstance.active = False

							if skillName in self.NEEDED_MODULES:
								moduleInstance.required = True

							self._deactivatedModules[moduleInstance.name] = moduleInstance
						continue

				self.checkModuleConditions(skillName, module['conditions'], availableModules)

				name = self.Commons.toCamelCase(skillName) if ' ' in skillName else skillName

				moduleInstance = self.importFromModule(skillName=name, isUpdate=isUpdate)

				if moduleInstance:

					if skillName in self.NEEDED_MODULES:
						moduleInstance.required = True

					modules[moduleInstance.name] = moduleInstance
				else:
					self._failedModules[name] = None
					
			except ModuleStartingFailed as e:
				self.logWarning(f'Failed loading module: {e}')
				continue
			except ModuleNotConditionCompliant as e:
				self.logInfo(f'Module {skillName} does not comply to "{e.condition}" condition, required "{e.conditionValue}"')
				continue
			except Exception as e:
				self.logWarning(f'Something went wrong loading module {skillName}: {e}')
				continue

		return dict(sorted(modules.items()))


	# noinspection PyTypeChecker
	def importFromModule(self, skillName: str, moduleResource: str = '', isUpdate: bool = False) -> Module:
		instance: Module = None

		moduleResource = moduleResource or skillName

		try:
			moduleImport = importlib.import_module(f'modules.{skillName}.{moduleResource}')

			if isUpdate:
				moduleImport = importlib.reload(moduleImport)

			klass = getattr(moduleImport, skillName)
			instance: Module = klass()
		except ImportError as e:
			self.logError(f"Couldn't import module {skillName}.{moduleResource}: {e}")
		except AttributeError as e:
			self.logError(f"Couldn't find main class for module {skillName}.{moduleResource}: {e}")
		except Exception as e:
			self.logError(f"Couldn't instantiate module {skillName}.{moduleResource}: {e}")

		return instance


	def onStop(self):
		super().onStop()

		for moduleItem in self._activeModules.values():
			moduleItem.onStop()
			self.logInfo(f"- Stopped!")


	def onFullHour(self):
		self.checkForModuleUpdates()


	def startAllModules(self):
		supportedIntents = list()

		tmp = self._activeModules.copy()
		for skillName, moduleItem in tmp.items():
			try:
				supportedIntents += self._startModule(moduleItem)
			except ModuleStartingFailed:
				continue
			except ModuleStartDelayed:
				self.logInfo(f'Module {skillName} start is delayed')

		supportedIntents = list(set(supportedIntents))

		self._supportedIntents = supportedIntents

		self.logInfo(f'All modules started. {len(supportedIntents)} intents supported')


	def _startModule(self, moduleInstance: Module) -> dict:
		try:
			name = moduleInstance.name
			intents = moduleInstance.onStart()

			if moduleInstance.widgets:
				self._widgets[name] = moduleInstance.widgets

			if intents:
				self.logInfo('- Started!')
				return intents
		except (ModuleStartingFailed, ModuleStartDelayed):
			raise
		except Exception as e:
			# noinspection PyUnboundLocalVariable
			self.logError(f'- Couldn\'t start module {name or "undefined"}. Did you forget to return the intents in onStart()? Error: {e}')

		return dict()


	def isModuleActive(self, skillName: str) -> bool:
		return skillName in self._activeModules


	def getModuleInstance(self, skillName: str, silent: bool = False) -> Optional[Module]:
		if skillName in self._activeModules:
			return self._activeModules[skillName]
		elif skillName in self._deactivatedModules:
			return self._deactivatedModules[skillName]
		else:
			if not silent:
				self.logWarning(f'Module "{skillName}" is disabled or does not exist in modules manager')

			return None


	def skillBroadcast(self, method: str, filterOut: list = None, silent: bool = False, *args, **kwargs):
		"""
		Broadcasts a call to the given method on every skill
		:param filterOut: array, skills not to broadcast to
		:param method: str, the method name to call on every skill
		:param args: arguments that should be passed
		:param silent
		:return:
		"""

		for moduleItem in self._activeModules.values():

			if filterOut and moduleItem.name in filterOut:
				continue

			try:
				func = getattr(moduleItem, method)
				func(*args, **kwargs)

			except AttributeError as e:
				if not silent:
					self.logWarning(f'Method "{method}" not found for module "{moduleItem.name}": {e}')
			except TypeError:
				# Do nothing, it's most prolly kwargs
				pass


	def deactivateModule(self, skillName: str, persistent: bool = False):
		if skillName in self._activeModules:
			self._activeModules[skillName].active = False
			self.ConfigManager.deactivateModule(skillName, persistent)
			self.configureModuleIntents(skillName=skillName, state=False)
			self._deactivatedModules[skillName] = self._activeModules.pop(skillName)


	def activateModule(self, skillName: str, persistent: bool = False):
		if skillName in self._deactivatedModules:
			self.ConfigManager.activateModule(skillName, persistent)
			self.configureModuleIntents(skillName=skillName, state=True)
			self._activeModules[skillName] = self._deactivatedModules.pop(skillName)
			self._activeModules[skillName].active = True
			self._activeModules[skillName].onStart()


	def checkForModuleUpdates(self, moduleToCheck: str = None) -> bool:
		if self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
			return False

		self.logInfo('Checking for module updates')
		if not self.InternetManager.online:
			self.logInfo('Not connected...')
			return False

		availableModules = self.ConfigManager.modulesConfigurations
		updateSource = self.ConfigManager.getSkillsUpdateSource()

		i = 0
		for skillName in self._allModules:
			try:
				if skillName not in availableModules or (moduleToCheck is not None and skillName != moduleToCheck):
					continue
	
				req = requests.get(f'https://raw.githubusercontent.com/project-alice-assistant/ProjectAliceModules/{updateSource}/PublishedModules/{availableModules[skillName]["author"]}/{skillName}/{skillName}.install')

				if req.status_code == 404:
					raise GithubNotFound

				remoteFile = req.json()
				if not remoteFile:
					raise Exception

				if Version(availableModules[skillName]['version']) < Version(remoteFile['version']):
					i += 1
					self.logInfo(f'❌ {skillName} - Version {availableModules[skillName]["version"]} < {remoteFile["version"]} in {self.ConfigManager.getAliceConfigByName("updateChannel")}')
	
					if not self.ConfigManager.getAliceConfigByName('moduleAutoUpdate'):
						if skillName in self._activeModules:
							self._activeModules[skillName].updateAvailable = True
						elif skillName in self._deactivatedModules:
							self._deactivatedModules[skillName].updateAvailable = True
					else:
						moduleFile = Path(self.Commons.rootDir(), 'system/moduleInstallTickets', skillName + '.install')
						moduleFile.write_text(json.dumps(remoteFile))
						if skillName in self._failedModules:
							del self._failedModules[skillName]
				else:
					self.logInfo(f'✔ {skillName} - Version {availableModules[skillName]["version"]} in {self.ConfigManager.getAliceConfigByName("updateChannel")}')

			except GithubNotFound:
				self.logInfo(f'❓ Module "{skillName}" is not available on Github. Deprecated or is it a dev module?')
						
			except Exception as e:
				self.logError(f'❗ Error checking updates for module "{skillName}": {e}')

		self.logInfo(f'Found {i} module update(s)')
		return i > 0


	def _checkForModuleInstall(self):
		self.ThreadManager.newTimer(interval=10, func=self._checkForModuleInstall, autoStart=True)

		root = Path(self.Commons.rootDir(), 'system/moduleInstallTickets')
		files = [f for f in root.iterdir() if f.suffix == '.install']

		if  self._busyInstalling.isSet() or \
			not self.InternetManager.online or \
			not files or \
			self.ThreadManager.getEvent('SnipsAssistantDownload').isSet():
			return

		if files:
			self.logInfo(f'Found {len(files)} install ticket(s)')
			self._busyInstalling.set()

			modulesToBoot = dict()
			try:
				modulesToBoot = self._installModules(files)
			except Exception as e:
				self._logger.error(f'Error installing module: {e}')
			finally:
				self.MqttManager.mqttBroadcast(topic='hermes/leds/clear')

				if modulesToBoot:
					for skillName, info in modulesToBoot.items():
						self._activeModules = self._loadModuleList(moduleToLoad=skillName, isUpdate=info['update'])
						self._allModules = {**self._allModules, **self._activeModules}

						try:
							self.LanguageManager.loadStrings(moduleToLoad=skillName)
							self.TalkManager.loadTalks(moduleToLoad=skillName)
						except:
							pass
					try:
						self.SamkillaManager.sync(moduleFilter=modulesToBoot)
					except Exception as esamk:
						self.logError(f'Failed syncing with remote snips console {esamk}')
						raise

				self._busyInstalling.clear()


	def _installModules(self, modules: list) -> dict:
		root = Path(self.Commons.rootDir(), 'system/moduleInstallTickets')
		availableModules = self.ConfigManager.modulesConfigurations
		modulesToBoot = dict()
		self.MqttManager.mqttBroadcast(topic='hermes/leds/systemUpdate', payload={'sticky': True})
		for file in modules:
			skillName = Path(file).with_suffix('')

			self.logInfo(f'Now taking care of module {skillName.stem}')
			res = root / file

			try:
				updating = False

				installFile = json.loads(res.read_text())

				skillName = installFile['name']
				path = Path(installFile['author'], skillName)

				if not skillName:
					self.logError('Module name to install not found, aborting to avoid casualties!')
					continue

				directory = Path(self.Commons.rootDir()) / 'modules' / skillName

				conditions = {
					'aliceMinVersion': installFile['aliceMinVersion'],
					**installFile.get('conditions', dict())
				}

				self.checkModuleConditions(skillName, conditions, availableModules)

				if skillName in availableModules:
					localVersionIsLatest: bool = \
						directory.is_dir() and \
						'version' in availableModules[skillName] and \
						Version(availableModules[skillName]['version']) >= Version(installFile['version'])

					if localVersionIsLatest:
						self.logWarning(f'Module "{skillName}" is already installed, skipping')
						subprocess.run(['sudo', 'rm', res])
						continue
					else:
						self.logWarning(f'Module "{skillName}" needs updating')
						updating = True

				if skillName in self._activeModules:
					try:
						self._activeModules[skillName].onStop()
					except Exception as e:
						self.logError(f'Error stopping "{skillName}" for update: {e}')
						raise

				gitCloner = GithubCloner(baseUrl=self.GITHUB_API_BASE_URL, path=path, dest=directory)

				try:
					gitCloner.clone()
					self.logInfo('Module successfully downloaded')
					self._installModule(res)
					modulesToBoot[skillName] = {
						'update': updating
					}
				except (GithubTokenFailed, GithubRateLimit):
					self.logError('Failed cloning module')
					raise
				except GithubNotFound:
					if self.ConfigManager.getAliceConfigByName('devMode'):
						if not Path(f'{self.Commons.rootDir}/modules/{skillName}').exists() or not \
								Path(f'{self.Commons.rootDir}/modules/{skillName}/{skillName.py}').exists() or not \
								Path(f'{self.Commons.rootDir}/modules/{skillName}/dialogTemplate').exists() or not \
								Path(f'{self.Commons.rootDir}/modules/{skillName}/talks').exists():
							self.logWarning(f'Module "{skillName}" cannot be installed in dev mode due to missing base files')
						else:
							self._installModule(res)
							modulesToBoot[skillName] = {
								'update': updating
							}
						continue
					else:
						self.logWarning(f'Module "{skillName}" is not available on Github, cannot install')
						raise
				except Exception:
					raise

			except ModuleNotConditionCompliant as e:
				self.logInfo(f'Module "{skillName}" does not comply to "{e.condition}" condition, required "{e.conditionValue}"')
				if res.exists():
					res.unlink()

				self.broadcast(
					method='onModuleInstallFailed',
					exceptions=self.name,
					module=skillName
				)

			except Exception as e:
				self.logError(f'Failed installing module "{skillName}": {e}')
				if res.exists():
					res.unlink()

				self.broadcast(
					method='onModuleInstallFailed',
					exceptions=self.name,
					module=skillName
				)
				raise

		return modulesToBoot


	def _installModule(self, res: Path):
		try:
			installFile = json.loads(res.read_text())
			pipReqs = installFile.get('pipRequirements', list())
			sysReqs = installFile.get('systemRequirements', list())
			scriptReq = installFile.get('script')
			directory = Path(self.Commons.rootDir()) / 'modules' / installFile['name']

			for requirement in pipReqs:
				subprocess.run(['./venv/bin/pip3', 'install', requirement])

			for requirement in sysReqs:
				subprocess.run(['sudo', 'apt-get', 'install', '-y', requirement])

			if scriptReq:
				subprocess.run(['sudo', 'chmod', '+x', str(directory / scriptReq)])
				subprocess.run(['sudo', str(directory / scriptReq)])

			node = {
				'active'    : True,
				'version'   : installFile['version'],
				'author'    : installFile['author'],
				'conditions': installFile['conditions']
			}

			shutil.move(str(res), str(directory))
			self.ConfigManager.addModuleToAliceConfig(installFile['name'], node)
		except Exception:
			raise


	def checkModuleConditions(self, skillName: str, conditions: dict, availableModules: dict) -> bool:

		if 'aliceMinVersion' in conditions and Version(conditions['aliceMinVersion']) > Version(constants.VERSION):
			raise ModuleNotConditionCompliant(message='Module is not compliant', skillName=skillName, condition='Alice minimum version', conditionValue=conditions['aliceMinVersion'])

		for conditionName, conditionValue in conditions.items():
			if conditionName == 'lang' and self.LanguageManager.activeLanguage not in conditionValue:
				raise ModuleNotConditionCompliant(message='Module is not compliant', skillName=skillName, condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'online':
				if conditionValue and self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
					raise ModuleNotConditionCompliant(message='Module is not compliant', skillName=skillName, condition=conditionName, conditionValue=conditionValue)
				elif not conditionValue and not self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
					raise ModuleNotConditionCompliant(message='Module is not compliant', skillName=skillName, condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'module':
				for requiredModule in conditionValue:
					if requiredModule['name'] in availableModules and not availableModules[requiredModule['name']]['active']:
						raise ModuleNotConditionCompliant(message='Module is not compliant', skillName=skillName, condition=conditionName, conditionValue=conditionValue)
					elif requiredModule['name'] not in availableModules:
						self.logInfo(f'Module {skillName} has another module as dependency, adding download')
						subprocess.run(['wget', requiredModule['url'], '-O', Path(self.Commons.rootDir(), f"system/moduleInstallTickets/{requiredModule['name']}.install")])

			elif conditionName == 'notModule':
				for excludedModule in conditionValue:
					author, name = excludedModule.split('/')
					if name in availableModules and availableModules[name]['author'] == author and availableModules[name]['active']:
						raise ModuleNotConditionCompliant(message='Module is not compliant', skillName=skillName, condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'asrArbitraryCapture':
				if conditionValue and not self.ASRManager.asr.capableOfArbitraryCapture:
					raise ModuleNotConditionCompliant(message='Module is not compliant', skillName=skillName, condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'activeManager':
				for manager in conditionValue:
					if not manager: continue

					man = SuperManager.getInstance().getManager(manager)
					if not man or not man.isActive:
						raise ModuleNotConditionCompliant(message='Module is not compliant', skillName=skillName, condition=conditionName, conditionValue=conditionValue)

		return True


	def configureModuleIntents(self, skillName: str, state: bool):
		try:
			module = self._activeModules.get(skillName, self._deactivatedModules.get(skillName))
			confs = [{
				'intentId': intent.justTopic if hasattr(intent, 'justTopic') else intent,
				'enable'  : state
			} for intent in module.supportedIntents if not self.isIntentInUse(intent=intent, filtered=[skillName])]

			self.MqttManager.configureIntents(confs)
		except Exception as e:
			self.logWarning(f'Intent configuration failed: {e}')


	def isIntentInUse(self, intent: Intent, filtered: list) -> bool:
		return any(intent in module.supportedIntents
		           for name, module in self._activeModules.items() if name not in filtered)


	def removeModule(self, skillName: str):
		if skillName not in {**self._activeModules, **self._deactivatedModules, **self._failedModules}:
			return

		self.configureModuleIntents(skillName, False)
		self.ConfigManager.removeModule(skillName)

		try:
			del self._activeModules[skillName]
		except KeyError:
			del self._deactivatedModules[skillName]

		shutil.rmtree(Path(self.Commons.rootDir(), 'modules', skillName))
		# TODO Samkilla cleaning
		self.SnipsConsoleManager.doDownload()
