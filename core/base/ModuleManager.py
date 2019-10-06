import collections
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
from core.commons import commons, constants

#Special case, must be called as last!
try:
	# noinspection PyUnresolvedReferences
	from modules.Customisation.Customisation import Customisation
except:
	# Load the sample file as dummy
	from modules.Customisation.Customisation_sample import Customisation


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


	def onSnipsAssistantDownloaded(self, *args: list, **kwargs: dict):
		argv = args[0] or dict()

		for moduleName, module in argv.items():
			if module['update']:
				method = 'onModuleUpdated'
				self._modules[moduleName]['instance'].onModuleUpdated()
			else:
				method = 'onModuleInstalled'
				self._modules[moduleName]['instance'].onModuleInstalled()

			SuperManager.getInstance().broadcast(
				method=method,
				exceptions=[constants.DUMMY],
				propagateToModules=False,
				args=[moduleName]
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
		self.broadcast('onBooted')
		self._moduleInstallThread.start()


	def _loadModuleList(self, moduleToLoad: str = '', isUpdate: bool = False) -> dict:
		if moduleToLoad:
			modules = self._modules.copy()
		else:
			modules = dict()

		availableModules = self.ConfigManager.modulesConfigurations
		availableModules = collections.OrderedDict(sorted(availableModules.items()))

		if Customisation.MODULE_NAME in availableModules:
			customisationModule = availableModules.pop(Customisation.MODULE_NAME)
			availableModules[Customisation.MODULE_NAME] = customisationModule

		for moduleName, module in availableModules.items():
			if moduleToLoad and moduleName != moduleToLoad:
				continue

			try:
				if not module['active']:
					if moduleName in self.NEEDED_MODULES:
						self._logger.info(f"Module {moduleName} marked as disable but it shouldn't be")
						SuperManager.getInstance().onStop()
						break
					else:
						self._logger.info(f'Module {moduleName} is disabled')

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

				if ' ' in moduleName:
					name = commons.toCamelCase(moduleName)
				else:
					name = moduleName

				moduleInstance = self.importFromModule(moduleName=name, isUpdate=isUpdate)

				if moduleInstance:

					if moduleName in self.NEEDED_MODULES:
						moduleInstance.required = True

					modules[moduleInstance.name] = {
						'instance': moduleInstance
					}
			except ModuleStartingFailed as e:
				self._logger.warning(f'[{self.name}] Failed loading module: {e}')
				continue
			except ModuleNotConditionCompliant as e:
				self._logger.info(f'[{self.name}] Module {moduleName} does not comply to "{e.condition}" condition, required "{e.conditionValue}"')
				continue
			except Exception as e:
				self._logger.warning(f'[{self.name}] Something went wrong loading a module: {e}')
				continue

		# noinspection PyTypeChecker
		return collections.OrderedDict(sorted(modules.items()))


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
			if moduleName != Customisation.MODULE_NAME:
				self._logger.error(f"[{self.name}] Couldn't import module {moduleName}.{moduleResource}: {e}")
		except AttributeError as e:
			self._logger.error(f"[{self.name}] Couldn't find main class for module {moduleName}.{moduleResource}: {e}")
		except Exception as e:
			self._logger.error(f"[{self.name}] Couldn't instanciate module {moduleName}.{moduleResource}: {e}")

		return instance


	def onStop(self):
		super().onStop()

		self._reorderCustomisationModule(True)
		for moduleItem in self._modules.values():
			moduleItem['instance'].onStop()
			self._logger.info(f"- [{moduleItem['instance'].name}] Stopped!")


	def onFullHour(self):
		self.checkForModuleUpdates()


	def startAllModules(self):
		supportedIntents = list()
		self._reorderCustomisationModule(True)

		tmp = self._modules.copy()
		for moduleName, moduleItem in tmp.items():
			try:
				supportedIntents += self._startModule(moduleItem['instance'])
			except ModuleStartingFailed:
				self._modules[moduleName]['active'] = False
			except ModuleStartDelayed:
				self._logger.info(f'[{self.name}] Module {moduleName} start is delayed')

		supportedIntents = list(set(supportedIntents))

		self._supportedIntents = supportedIntents

		self._logger.info(f'[{self.name}] All modules started. {len(supportedIntents)} intents supported')


	def _startModule(self, moduleInstance: Module) -> list:
		name = 'undefined'

		try:
			name = moduleInstance.name
			intents = moduleInstance.onStart()

			if moduleInstance.widgets:
				self._widgets[name] = moduleInstance.widgets

			if intents:
				self._logger.info('- Started!')
				return intents
		except ModuleStartingFailed:
			raise
		except ModuleStartDelayed:
			raise
		except Exception as e:
			self._logger.error(f'- Couldn\'t start module {name}. Did you forget to return the intents in onStart()? Error: {e}')

		return list()


	def isModuleActive(self, moduleName: str) -> bool:
		return moduleName in self._modules


	def getModuleInstance(self, moduleName: str) -> Optional[Module]:
		if moduleName not in self._modules:
			if moduleName != Customisation.MODULE_NAME:
				self._logger.warning(f'[{self.name}] Module "{moduleName}" is disabled or does not exist in modules manager')
			return None
		else:
			return self._modules[moduleName]['instance']


	def getModules(self, isEvent: bool = False) -> dict:
		self._reorderCustomisationModule(isEvent)
		return self._modules


	def broadcast(self, method: str, isEvent: bool = True, filterOut: list = None, silent: bool = False, args: list = None):
		"""
		Boradcasts a call to the given method on every module
		:param filterOut: array, module not to boradcast to
		:param method: str, the method name to call on every module
		:param isEvent: bool, is this broadcast initiated by an event or a user interaction? Changes for customisation module call
		:param args: arguments that should be passed
		:param silent
		:return:
		"""
		if not args:
			args = list()

		self._reorderCustomisationModule(isEvent)
		for moduleItem in self._modules.values():
			if filterOut and moduleItem['instance'].name in filterOut:
				continue

			try:
				func = getattr(moduleItem['instance'], method)
				func(*args)
			except Exception as e:
				if not silent:
					self._logger.warning(f'[{self.name}] Method "{method}" not found for module "{moduleItem["instance"].name}": {e}')


	def _reorderCustomisationModule(self, isEvent: bool):
		"""
		If it's an event call, customisationModule should go last in line. If it's a message call, customisationModule should go first
		:param isEvent: bool
		"""

		if Customisation.MODULE_NAME not in self._modules:
			return #Customisation module might be disabled

		if isEvent:
			if list(self._modules.items())[0][0] == Customisation.MODULE_NAME:
				customisationModule = self._modules.pop(Customisation.MODULE_NAME)
				self._modules[Customisation.MODULE_NAME] = customisationModule
		else:
			if list(self._modules.items())[0][0] != Customisation.MODULE_NAME:
				customisationModule = self._modules.pop(Customisation.MODULE_NAME)
				modules = self._modules.copy()
				self._modules = collections.OrderedDict()
				self._modules[Customisation.MODULE_NAME] = customisationModule
				self._modules.update(modules)


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

		self._logger.info(f'[{self.name}] Checking for module updates')
		if not self.InternetManager.online:
			self._logger.info(f'[{self.name}] Not connected...')
			return

		availableModules = self.ConfigManager.modulesConfigurations

		i = 0
		for moduleName in self._modules:
			try:
				if moduleName not in availableModules:
					continue

				req = requests.get(f'https://raw.githubusercontent.com/project-alice-powered-by-snips/ProjectAliceModules/master/PublishedModules/{availableModules[moduleName]["author"]}/{moduleName}/{moduleName}.install')

				remoteFile = req.json()
				if float(remoteFile['version']) > float(availableModules[moduleName]['version']):
					i += 1

					if not self.ConfigManager.getAliceConfigByName('moduleAutoUpdate'):
						if moduleName in self._modules:
							self._modules[moduleName]['instance'].updateAvailable = True
						elif moduleName in self._deactivatedModules:
							self._deactivatedModules[moduleName]['instance'].updateAvailable = True
					else:
						moduleFile = Path(commons.rootDir(), 'system/moduleInstallTickets', moduleName + '.install')
						moduleFile.write_text(json.dumps(remoteFile))

			except Exception as e:
				self._logger.warning(f'[{self.name}] Error checking updates for module "{moduleName}": {e}')

		self._logger.info(f'[{self.name}] Found {i} module update(s)')


	def _checkForModuleInstall(self):
		self.ThreadManager.newTimer(interval=10, func=self._checkForModuleInstall, autoStart=True)

		root = Path(commons.rootDir(), 'system/moduleInstallTickets')
		files = [f for f in root.iterdir() if f.suffix == '.install']

		if  self._busyInstalling.isSet() or \
			not self.InternetManager.online or \
			not files or \
			self.ThreadManager.getEvent('SnipsAssistantDownload').isSet():
			return

		if files:
			self._logger.info(f'[{self.name}] Found {len(files)} install ticket(s)')
			self._busyInstalling.set()

			modulesToBoot = list()
			try:
				modulesToBoot = self._installModules(files)
			except Exception as e:
				self._logger.error(f'[{self.name}] Error checking for module install: {e}')
			finally:
				if modulesToBoot:
					try:
						self.SamkillaManager.sync(moduleFilter=modulesToBoot)
					except Exception as esamk:
						self._logger.error(f'[{self.name}] Failed syncing with remote snips console {esamk}')
						raise

					for moduleName, info in modulesToBoot.items():
						self._modules = self._loadModuleList(moduleToLoad=moduleName, isUpdate=info['update'])

						try:
							self.LanguageManager.loadStrings(moduleToLoad=moduleName)
							self.TalkManager.loadTalks(moduleToLoad=moduleName)

							if info['update']:
								self._modules[moduleName]['instance'].onModuleUpdated()
							else:
								self._modules[moduleName]['instance'].onModuleInstalled()

							self._startModule(moduleInstance=self._modules[moduleName]['instance'])
							self._modules[moduleName]['instance'].onBooted()
						except:
							pass

					self.SnipsServicesManager.runCmd(cmd='restart')

				self._busyInstalling.clear()


	def _installModules(self, modules: list) -> dict:
		root = Path(commons.rootDir(), 'system/moduleInstallTickets')
		availableModules = self.ConfigManager.modulesConfigurations
		modulesToBoot = dict()
		self.MqttManager.broadcast(topic='hermes/leds/systemUpdate', payload={'sticky': True})
		for file in modules:
			moduleName = Path(file).with_suffix('')

			self._logger.info(f'[{self.name}] Now taking care of module {moduleName.stem}')
			res = root / file

			try:
				updating = False

				installFile = json.loads(res.read_text())

				moduleName = installFile['name']
				path = Path(installFile['author'], moduleName)

				if not moduleName:
					self._logger.error(f'[{self.name}] Module name to install not found, aborting to avoid casualties!')
					continue

				directory = Path(commons.rootDir()) / 'modules' / moduleName

				conditions = {
					'aliceMinVersion': installFile['aliceMinVersion']
				}

				if 'conditions' in installFile:
					conditions = {**conditions, **installFile['conditions']}

				self.checkModuleConditions(moduleName, conditions, availableModules)

				if moduleName in availableModules:
					localVersionDirExists = directory.is_dir()
					localVersionAttributeExists: bool = 'version' in availableModules[moduleName]

					localVersionIsLatest: bool = \
						localVersionDirExists and \
						localVersionAttributeExists and \
						float(availableModules[moduleName]['version']) >= float(installFile['version'])

					if localVersionIsLatest:
						self._logger.warning(f'[{self.name}] Module "{moduleName}" is already installed, skipping')
						subprocess.run(['sudo', 'rm', res])
						continue
					else:
						self._logger.warning(f'[{self.name}] Module "{moduleName}" needs updating')
						updating = True

				if moduleName in self._modules:
					try:
						self._modules[moduleName]['instance'].onStop()
					except Exception as e:
						self._logger.error(f'[{self.name}] Error stopping "{moduleName}" for update: {e}')
						raise

				gitCloner = GithubCloner(baseUrl=self.GITHUB_API_BASE_URL, path=path, dest=directory)

				if gitCloner.clone():
					self._logger.info(f'[{self.name}] Module successfully downloaded')
					try:
						pipReq = installFile.get('pipRequirements', None)
						sysReq = installFile.get('systemRequirements', None)
						scriptReq = installFile.get('script', None)

						if pipReq:
							for requirement in pipReq:
								subprocess.run(['./venv/bin/pip3', 'install', requirement])

						if sysReq:
							for requirement in sysReq:
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
						self._logger.error(f'[{self.name}] Failed installing module "{moduleName}": {e}')
						res.unlink()
						SuperManager.getInstance().broadcast(
							method='onModuleInstallFailed',
							exceptions=self.name,
							propagateToModules=False,
							args=[self.name]
						)
				else:
					self._logger.error(f'[{self.name}] Failed cloning module')
					res.unlink()
					SuperManager.getInstance().broadcast(
						method='onModuleInstallFailed',
						exceptions=self.name,
						propagateToModules=False,
						args=[self.name]
					)

			except ModuleNotConditionCompliant as e:
				self._logger.info(f'[{self.name}] Module {moduleName} does not comply to "{e.condition}" condition, required "{e.conditionValue}"')
				res.unlink()
				SuperManager.getInstance().broadcast(
					method='onModuleInstallFailed',
					exceptions=self.name,
					propagateToModules=False,
					args=[self.name]
				)

			except Exception as e:
				self._logger.error(f'[{self.name}] Failed installing module "{moduleName}": {e}')
				res.unlink()
				SuperManager.getInstance().broadcast(
					method='onModuleInstallFailed',
					exceptions=self.name,
					propagateToModules=False,
					args=[self.name]
				)

		self.MqttManager.broadcast(topic='hermes/leds/clear')
		return modulesToBoot


	def checkModuleConditions(self, moduleName: str, conditions: dict, availableModules: dict) -> bool:

		if 'aliceMinVersion' in conditions and conditions['aliceMinVersion'] > constants.VERSION:
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
						self._logger.info(f'[{self.name}] Module {moduleName} has another module as dependency, adding download')
						subprocess.run(['wget', requiredModule['url'], '-O', Path(commons.rootDir(), f"system/moduleInstallTickets/{requiredModule['name']}.install")])

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
			confs = list()
			module = self._modules.get(moduleName, self._deactivatedModules.get(moduleName))['instance']
			for intent in module.supportedIntents:
				if self.isIntentInUse(intent=intent, filtered=[moduleName]):
					continue

				confs.append({
					'intentId': intent.justTopic if hasattr(intent, 'justTopic') else intent,
					'enable'  : state
				})

			self.MqttManager.configureIntents(confs)
		except Exception as e:
			self._logger.warning(f'[{self.name}] Intent configuration failed: {e}')


	def isIntentInUse(self, intent: Intent, filtered: list) -> bool:
		for moduleName, module in self._modules.items():
			if moduleName in filtered:
				continue

			if intent in module['instance'].supportedIntents:
				return True

		return False


	def removeModule(self, moduleName: str):
		if not moduleName in self._modules:
			return
		else:
			self.configureModuleIntents(moduleName, False)
			self.ConfigManager.removeModule(moduleName)
			del self._modules[moduleName]

		shutil.rmtree(Path(commons.rootDir(), 'modules', moduleName))
		# TODO Samkilla cleaning
		self.SnipsConsoleManager.doDownload()
