import importlib
import json
import subprocess
from pathlib import Path
from typing import Optional

import requests
import shutil

from core.ProjectAliceExceptions import ModuleNotConditionCompliant, ModuleStartDelayed, ModuleStartingFailed
from core.base.SuperManager import SuperManager
from core.base.model import Intent
from core.base.model.GithubCloner import GithubCloner
from core.base.model.Manager import Manager
from core.base.model.Module import Module
from core.base.model.Version import Version
from core.commons import constants


class ModuleManager(Manager):

	NAME = 'ModuleManager'

	NEEDED_MODULES = [
		'AliceCore',
		'ContextSensitive',
		'RedQueen'
	]

	GITHUB_BARE_BASE_URL = 'https://raw.githubusercontent.com/project-alice-powered-by-snips/ProjectAliceModules/master/PublishedModules'
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
		self._modules               = dict()
		self._failedModules         = dict()
		self._deactivatedModules    = dict()
		self._widgets               = dict()


	def onStart(self):
		super().onStart()

		self._busyInstalling = self.ThreadManager.newEvent('moduleInstallation')
		self._moduleInstallThread = self.ThreadManager.newThread(name='ModuleInstallThread', target=self._checkForModuleInstall, autostart=False)

		self._modules = self._loadModuleList()

		for moduleName in self._deactivatedModules:
			self.configureModuleIntents(moduleName=moduleName, state=False)

		self.checkForModuleUpdates()
		self.startAllModules()


	def onSnipsAssistantDownloaded(self, **kwargs):
		argv = kwargs.get('modulesInfos', dict())
		if not argv:
			return

		for moduleName, module in argv.items():
			try:
				self._startModule(moduleInstance=self._modules[moduleName]['instance'])
			except ModuleStartDelayed:
				self.logInfo(f'Module "{moduleName}" start is delayed')

			self._modules[moduleName]['instance'].onBooted()

			self.broadcast(
				method='onModuleUpdated' if module['update'] else 'onModuleInstalled',
				exceptions=[constants.DUMMY],
				module=moduleName
			)


	@property
	def widgets(self) -> dict:
		return self._widgets


	@property
	def supportedIntents(self) -> list:
		return self._supportedIntents


	@property
	def deactivatedModules(self) -> dict:
		return self._deactivatedModules


	def onBooted(self):
		self.moduleBroadcast('onBooted')
		self._moduleInstallThread.start()


	def _loadModuleList(self, moduleToLoad: str = '', isUpdate: bool = False) -> dict:
		modules = self._modules.copy() if moduleToLoad else dict()

		availableModules = self.ConfigManager.modulesConfigurations
		availableModules = dict(sorted(availableModules.items()))

		for moduleName, module in availableModules.items():
			if moduleToLoad and moduleName != moduleToLoad:
				continue

			try:
				if not module['active']:
					if moduleName in self.NEEDED_MODULES:
						self.logInfo(f"Module {moduleName} marked as disable but it shouldn't be")
						self.ProjectAlice.onStop()
						break
					else:
						self.logInfo(f'Module {moduleName} is disabled')

						moduleInstance = self.importFromModule(moduleName=moduleName, isUpdate=False)
						if moduleInstance:
							moduleInstance.active = False

							if moduleName in self.NEEDED_MODULES:
								moduleInstance.required = True

							self._deactivatedModules[moduleInstance.name] = {
								'instance': moduleInstance
							}
						continue

				self.checkModuleConditions(moduleName, module['conditions'], availableModules)

				name = self.Commons.toCamelCase(moduleName) if ' ' in moduleName else moduleName

				moduleInstance = self.importFromModule(moduleName=name, isUpdate=isUpdate)

				if moduleInstance:

					if moduleName in self.NEEDED_MODULES:
						moduleInstance.required = True

					# TODO refacto this to modules[moduleInstance.name] = moduleInstance. The dict is useless here
					modules[moduleInstance.name] = {
						'instance': moduleInstance
					}
				else:
					self._failedModules[name] = { 
						'instance': None
					}
					
			except ModuleStartingFailed as e:
				self.logWarning(f'Failed loading module: {e}')
				continue
			except ModuleNotConditionCompliant as e:
				self.logInfo(f'Module {moduleName} does not comply to "{e.condition}" condition, required "{e.conditionValue}"')
				continue
			except Exception as e:
				self.logWarning(f'Something went wrong loading module {moduleName}: {e}')
				continue

		return dict(sorted(modules.items()))


	# noinspection PyTypeChecker
	def importFromModule(self, moduleName: str, moduleResource: str = '', isUpdate: bool = False) -> Module:
		instance: Module = None

		moduleResource = moduleResource or moduleName

		try:
			moduleImport = importlib.import_module(f'modules.{moduleName}.{moduleResource}')

			if isUpdate:
				moduleImport = importlib.reload(moduleImport)

			klass = getattr(moduleImport, moduleName)
			instance: Module = klass()
		except ImportError as e:
			self.logError(f"Couldn't import module {moduleName}.{moduleResource}: {e}")
		except AttributeError as e:
			self.logError(f"Couldn't find main class for module {moduleName}.{moduleResource}: {e}")
		except Exception as e:
			self.logError(f"Couldn't instanciate module {moduleName}.{moduleResource}: {e}")

		return instance


	def onStop(self):
		super().onStop()

		for moduleItem in self._modules.values():
			moduleItem['instance'].onStop()
			self.logInfo(f"- Stopped!")


	def onFullHour(self):
		self.checkForModuleUpdates()


	def startAllModules(self):
		supportedIntents = list()

		tmp = self._modules.copy()
		for moduleName, moduleItem in tmp.items():
			try:
				supportedIntents += self._startModule(moduleItem['instance'])
			except ModuleStartingFailed:
				continue
			except ModuleStartDelayed:
				self.logInfo(f'Module {moduleName} start is delayed')

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


	def isModuleActive(self, moduleName: str) -> bool:
		return moduleName in self._modules


	def getModuleInstance(self, moduleName: str, silent: bool = False) -> Optional[Module]:
		if moduleName in self._modules:
			return self._modules[moduleName]['instance']

		if not silent:
			self.logWarning(f'Module "{moduleName}" is disabled or does not exist in modules manager')
		return


	def getModules(self) -> dict:
		return self._modules


	def moduleBroadcast(self, method: str, filterOut: list = None, silent: bool = False, *args, **kwargs):
		"""
		Broadcasts a call to the given method on every module
		:param filterOut: array, module not to broadcast to
		:param method: str, the method name to call on every module
		:param args: arguments that should be passed
		:param silent
		:return:
		"""

		for moduleItem in self._modules.values():

			if filterOut and moduleItem['instance'].name in filterOut:
				continue

			try:
				func = getattr(moduleItem['instance'], method)
				func(*args, **kwargs)

			except AttributeError as e:
				if not silent:
					self.logWarning(f'Method "{method}" not found for module "{moduleItem["instance"].name}": {e}')
			except TypeError:
				# Do nothing, it's most prolly kwargs
				pass


	def deactivateModule(self, moduleName: str, persistent: bool = False):
		if moduleName in self._modules:
			self._modules[moduleName]['instance'].active = False
			self.ConfigManager.deactivateModule(moduleName, persistent)
			self.configureModuleIntents(moduleName=moduleName, state=False)
			self._deactivatedModules[moduleName] = self._modules.pop(moduleName)


	def activateModule(self, moduleName: str, persistent: bool = False):
		if moduleName in self._deactivatedModules:
			self.ConfigManager.activateModule(moduleName, persistent)
			self.configureModuleIntents(moduleName=moduleName, state=True)
			self._modules[moduleName] = self._deactivatedModules.pop(moduleName)
			self._modules[moduleName]['instance'].active = True
			self._modules[moduleName]['instance'].onStart()


	def checkForModuleUpdates(self):
		if self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
			return

		self.logInfo('Checking for module updates')
		if not self.InternetManager.online:
			self.logInfo('Not connected...')
			return

		availableModules = self.ConfigManager.modulesConfigurations
		updateSource = self.ConfigManager.getModulesUpdateSource()

		i = 0
		for moduleName in {**self._modules, **self._failedModules}:
			try:
				if moduleName not in availableModules:
					continue
	
				req = requests.get(f'https://raw.githubusercontent.com/project-alice-powered-by-snips/ProjectAliceModules/{updateSource}/PublishedModules/{availableModules[moduleName]["author"]}/{moduleName}/{moduleName}.install')
	
				remoteFile = req.json()
				if not remoteFile:
					raise Exception

				if Version(availableModules[moduleName]['version']) < Version(remoteFile['version']):
					i += 1
					self.logInfo(f'❌ {moduleName} - Version {availableModules[moduleName]["version"]} < {remoteFile["version"]} in {self.ConfigManager.getAliceConfigByName("updateChannel")}')
	
					if not self.ConfigManager.getAliceConfigByName('moduleAutoUpdate'):
						if moduleName in self._modules:
							self._modules[moduleName]['instance'].updateAvailable = True
						elif moduleName in self._deactivatedModules:
							self._deactivatedModules[moduleName]['instance'].updateAvailable = True
					else:
						moduleFile = Path(self.Commons.rootDir(), 'system/moduleInstallTickets', moduleName + '.install')
						moduleFile.write_text(json.dumps(remoteFile))
						if moduleName in self._failedModules:
							del self._failedModules[moduleName]
				else:
					self.logInfo(f'✔ {moduleName} - Version {availableModules[moduleName]["version"]} in {self.ConfigManager.getAliceConfigByName("updateChannel")}')
						
			except Exception as e:
				self.logError(f'Error checking updates for module "{moduleName}": {e}')

		self.logInfo(f'Found {i} module update(s)')


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
				if modulesToBoot:
					for moduleName, info in modulesToBoot.items():
						self._modules = self._loadModuleList(moduleToLoad=moduleName, isUpdate=info['update'])

						try:
							self.LanguageManager.loadStrings(moduleToLoad=moduleName)
							self.TalkManager.loadTalks(moduleToLoad=moduleName)
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
			moduleName = Path(file).with_suffix('')

			self.logInfo(f'Now taking care of module {moduleName.stem}')
			res = root / file

			try:
				updating = False

				installFile = json.loads(res.read_text())

				moduleName = installFile['name']
				path = Path(installFile['author'], moduleName)

				if not moduleName:
					self.logError('Module name to install not found, aborting to avoid casualties!')
					continue

				directory = Path(self.Commons.rootDir()) / 'modules' / moduleName

				conditions = {
					'aliceMinVersion': installFile['aliceMinVersion'],
					**installFile.get('conditions', dict())
				}

				self.checkModuleConditions(moduleName, conditions, availableModules)

				if moduleName in availableModules:
					localVersionIsLatest: bool = \
						directory.is_dir() and \
						'version' in availableModules[moduleName] and \
						Version(availableModules[moduleName]['version']) >= Version(installFile['version'])

					if localVersionIsLatest:
						self.logWarning(f'Module "{moduleName}" is already installed, skipping')
						subprocess.run(['sudo', 'rm', res])
						continue
					else:
						self.logWarning(f'Module "{moduleName}" needs updating')
						updating = True

				if moduleName in self._modules:
					try:
						self._modules[moduleName]['instance'].onStop()
					except Exception as e:
						self.logError(f'Error stopping "{moduleName}" for update: {e}')
						raise

				gitCloner = GithubCloner(baseUrl=self.GITHUB_API_BASE_URL, path=path, dest=directory)

				if gitCloner.clone():
					self.logInfo('Module successfully downloaded')
					try:
						pipReqs = installFile.get('pipRequirements', list())
						sysReqs = installFile.get('systemRequirements', list())
						scriptReq = installFile.get('script')

						for requirement in pipReqs:
							subprocess.run(['./venv/bin/pip3', 'install', requirement])

						for requirement in sysReqs:
							subprocess.run(['sudo', 'apt-get', 'install', '-y', requirement])

						if scriptReq:
							subprocess.run(['sudo', 'chmod', '+x', str(directory / scriptReq)])
							subprocess.run(['sudo', str(directory / scriptReq)])

						node = {
							'active': True,
							'version': installFile['version'],
							'author': installFile['author'],
							'conditions': installFile['conditions']
						}

						self.ConfigManager.addModuleToAliceConfig(installFile['name'], node)
						subprocess.run(['mv', res, directory])
						modulesToBoot[moduleName] = {
							'update': updating
						}
					except Exception as e:
						self.logError(f'Failed installing module "{moduleName}": {e}')
						res.unlink()
						self.broadcast(
							method='onModuleInstallFailed',
							exceptions=self.name,
							module=moduleName
						)
				else:
					self.logError('Failed cloning module')
					res.unlink()
					self.broadcast(
						method='onModuleInstallFailed',
						exceptions=self.name,
						module=moduleName
					)

			except ModuleNotConditionCompliant as e:
				self.logInfo(f'Module {moduleName} does not comply to "{e.condition}" condition, required "{e.conditionValue}"')
				res.unlink()
				self.broadcast(
					method='onModuleInstallFailed',
					exceptions=self.name,
					module=moduleName
				)

			except Exception as e:
				self.logError(f'Failed installing module "{moduleName}": {e}')
				res.unlink()
				self.broadcast(
					method='onModuleInstallFailed',
					exceptions=self.name,
					module=moduleName
				)

		self.MqttManager.mqttBroadcast(topic='hermes/leds/clear')
		return modulesToBoot


	def checkModuleConditions(self, moduleName: str, conditions: dict, availableModules: dict) -> bool:

		if 'aliceMinVersion' in conditions and Version(conditions['aliceMinVersion']) > Version(constants.VERSION):
			raise ModuleNotConditionCompliant(message='Module is not compliant', moduleName=moduleName, condition='Alice minimum version', conditionValue=conditions['aliceMinVersion'])

		for conditionName, conditionValue in conditions.items():
			if conditionName == 'lang' and self.LanguageManager.activeLanguage not in conditionValue:
				raise ModuleNotConditionCompliant(message='Module is not compliant', moduleName=moduleName, condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'online':
				if conditionValue and self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
					raise ModuleNotConditionCompliant(message='Module is not compliant', moduleName=moduleName, condition=conditionName, conditionValue=conditionValue)
				elif not conditionValue and not self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
					raise ModuleNotConditionCompliant(message='Module is not compliant', moduleName=moduleName, condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'module':
				for requiredModule in conditionValue:
					if requiredModule['name'] in availableModules and not availableModules[requiredModule['name']]['active']:
						raise ModuleNotConditionCompliant(message='Module is not compliant', moduleName=moduleName, condition=conditionName, conditionValue=conditionValue)
					elif requiredModule['name'] not in availableModules:
						self.logInfo(f'Module {moduleName} has another module as dependency, adding download')
						subprocess.run(['wget', requiredModule['url'], '-O', Path(self.Commons.rootDir(), f"system/moduleInstallTickets/{requiredModule['name']}.install")])

			elif conditionName == 'notModule':
				for excludedModule in conditionValue:
					author, name = excludedModule.split('/')
					if name in availableModules and availableModules[name]['author'] == author and availableModules[name]['active']:
						raise ModuleNotConditionCompliant(message='Module is not compliant', moduleName=moduleName, condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'asrArbitraryCapture':
				if conditionValue and not self.ASRManager.asr.capableOfArbitraryCapture:
					raise ModuleNotConditionCompliant(message='Module is not compliant', moduleName=moduleName, condition=conditionName, conditionValue=conditionValue)

			elif conditionName == 'activeManager':
				for manager in conditionValue:
					if not manager: continue

					man = SuperManager.getInstance().getManager(manager)
					if not man or not man.isActive:
						raise ModuleNotConditionCompliant(message='Module is not compliant', moduleName=moduleName, condition=conditionName, conditionValue=conditionValue)

		return True


	def configureModuleIntents(self, moduleName: str, state: bool):
		try:
			module = self._modules.get(moduleName, self._deactivatedModules.get(moduleName))['instance']
			confs = [{
				'intentId': intent.justTopic if hasattr(intent, 'justTopic') else intent,
				'enable'  : state
			} for intent in module.supportedIntents if not self.isIntentInUse(intent=intent, filtered=[moduleName])]

			self.MqttManager.configureIntents(confs)
		except Exception as e:
			self.logWarning(f'Intent configuration failed: {e}')


	def isIntentInUse(self, intent: Intent, filtered: list) -> bool:
		return any(intent in module['instance'].supportedIntents
			for name, module in self._modules.items() if name not in filtered)


	def removeModule(self, moduleName: str):
		if moduleName not in self._modules:
			return

		self.configureModuleIntents(moduleName, False)
		self.ConfigManager.removeModule(moduleName)
		del self._modules[moduleName]

		shutil.rmtree(Path(self.Commons.rootDir(), 'modules', moduleName))
		# TODO Samkilla cleaning
		self.SnipsConsoleManager.doDownload()
