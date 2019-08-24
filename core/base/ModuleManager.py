# -*- coding: utf-8 -*-

import collections
import fnmatch
import importlib
import json
import subprocess

import os
from typing import Optional

import requests

from core.commons import commons
import core.base.Managers as managers
from core.base.Manager import Manager
from core.base.model.Module import Module
from core.ProjectAliceExceptions import ModuleStartingFailed, ModuleStartDelayed, ModuleNotConditionCompliant
from core.base.model.GithubCloner import GithubCloner

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
		'ContextSensitive'
	]

	GITHUB_BARE_BASE_URL = 'https://raw.githubusercontent.com/project-alice-powered-by-snips/ProjectAliceModules/master/PublishedModules'
	GITHUB_API_BASE_URL = 'repositories/193512918/contents/PublishedModules'

	def __init__(self, mainClass):
		super().__init__(mainClass, self.NAME)

		managers.ModuleManager = self
		self._busyInstalling = managers.ThreadManager.newLock('moduleInstallation')

		self._moduleInstallThread = managers.ThreadManager.newThread(name = 'ModuleInstallThread', target = self._checkForModuleInstall, autostart = False)
		self._modules = self._loadModuleList()
		self._supportedIntents = list()


	@property
	def supportedIntents(self):
		return self._supportedIntents


	def onBooted(self):
		self.broadcast('onBooted')
		self._moduleInstallThread.start()


	def _loadModuleList(self, moduleToLoad: str = '', isUpdate: bool = False):
		if moduleToLoad:
			modules = self._modules.copy()
		else:
			modules = dict()

		availableModules = managers.ConfigManager.modulesConfigurations
		availableModules = collections.OrderedDict(sorted(availableModules.items()))

		customisationModule = availableModules.pop(Customisation.MODULE_NAME)
		availableModules[Customisation.MODULE_NAME] = customisationModule

		for moduleName, module in availableModules.items():
			if moduleToLoad and moduleName != moduleToLoad:
				continue

			try:
				if not module['active']:
					if moduleName in self.NEEDED_MODULES:
						self._logger.info("Module {} marked as disable but it shouldn't be".format(moduleName))
					else:
						self._logger.info('Module {} is disabled'.format(moduleName))
						continue

				if 'conditions' in module.keys():
					for conditionName, conditionValue in module['conditions'].items():
						if conditionName == 'lang' and managers.LanguageManager.activeLanguage not in conditionValue:
							raise ModuleNotConditionCompliant
						elif conditionName == 'online':
							if conditionValue and managers.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
								raise ModuleNotConditionCompliant
							elif not conditionValue and not managers.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
								raise ModuleNotConditionCompliant
						elif conditionName == 'module':
							for requiredModule in conditionValue:
								if requiredModule['name'] in availableModules and not availableModules[requiredModule['name']]['active']:
									raise ModuleNotConditionCompliant
								elif requiredModule['name'] not in availableModules:
									self._logger.info('[{}] Module {} has another module as dependency, adding download'.format(self.name, moduleName))
									subprocess.run(['wget', requiredModule['url'], '-O', '{}/system/moduleInstallTickets/{}.install'.format(commons.rootDir(), requiredModule['name'])])
						elif conditionName == 'asrArbitraryCapture':
							if conditionValue and not managers.ASRManager.asr.capableOfArbitraryCapture:
								raise ModuleNotConditionCompliant

				if ' ' in moduleName:
					name = commons.toCamelCase(moduleName)
				else:
					name = moduleName

				moduleInstance = self.importFromModule(moduleName = name, isUpdate = isUpdate)

				if moduleInstance:
					modules[moduleInstance.name] = {
						'instance': moduleInstance
					}
			except ModuleStartingFailed as e:
				self._logger.warning('[{}] Failed loading module: {}'.format(self.name, e))
				continue
			except ModuleNotConditionCompliant:
				self._logger.info('Module {} does not comply to "{}" condition, required "{}"'.format(moduleName, conditionName, conditionValue))
				continue
			except Exception:
				continue

		return collections.OrderedDict(sorted(modules.items()))


	# noinspection PyTypeChecker
	def importFromModule(self, moduleName: str, moduleResource: str = '', isUpdate: bool = False) -> Module:
		instance: Module = None

		moduleResource = moduleName if not moduleResource else moduleResource

		try:
			moduleImport = importlib.import_module('modules.{}.{}'.format(moduleName, moduleResource))

			if isUpdate:
				moduleImport = importlib.reload(moduleImport)

			klass = getattr(moduleImport, moduleName)
			instance: Module = klass()
		except ImportError as e:
			if moduleName != Customisation.MODULE_NAME:
				self._logger.error("[{}] Couldn't import module {}.{}: {}".format(self.name, moduleName, moduleResource, e))
		except AttributeError as e:
			self._logger.error("[{}] Couldn't find main class for module {}.{}: {}".format(self.name, moduleName, moduleResource, e))
		except Exception as e:
			self._logger.error("[{}] Couldn't instanciate module {}.{}: {}".format(self.name, moduleName, moduleResource, e))

		return instance


	def onStart(self):
		super().onStart()
		self.checkForModuleUpdates()
		self.startAllModules()


	def onStop(self):
		super().onStop()

		self._reorderCustomisationModule(True)
		for moduleItem in self._modules.values():
			moduleItem['instance'].onStop()
			self._logger.info('- [{}] Stopped!'.format(moduleItem['instance'].name))


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
				pass

		supportedIntents = list(set(supportedIntents))

		self._supportedIntents = supportedIntents

		self._logger.info('[{}] All modules started. {} intents supported'.format(self.name, len(supportedIntents)))


	def _startModule(self, moduleInstance: Module) -> list:
		name = 'undefined'

		try:
			name = moduleInstance.name
			intents = moduleInstance.onStart()
			if intents:
				self._logger.info('- Started!')
				return intents
		except ModuleStartingFailed:
			pass
		except ModuleStartDelayed:
			pass
		except Exception as e:
			self._logger.error('- Coulnd\'t start module {}. Did you forget to return the intents in onStart()? Error: {}'.format(name, e))

		return []


	def isModuleActive(self, moduleName: str) -> bool:
		return moduleName in self._modules


	def getModuleInstance(self, moduleName: str) -> Optional[Module]:
		if moduleName not in self._modules:
			if moduleName != Customisation.MODULE_NAME:
				self._logger.warning('[{}] Module "{}" is disabled or does not exist in modules manager'.format(self.name, moduleName))
			return None
		else:
			return self._modules[moduleName]['instance']


	def getModules(self, isEvent: bool = False) -> dict:
		self._reorderCustomisationModule(isEvent)
		return self._modules


	def broadcast(self, method: str, isEvent: bool = True, filterOut: list = None, args: list = None):
		"""
		Boradcasts a call to the given method on every module
		:param filterOut: array, module not to boradcast to
		:param method: str, the method name to call on every module
		:param isEvent: bool, is this broadcast initiated by an event or a message? Changes for customisation module call
		:param args: arguments that should be passed
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
			except: pass


	def _reorderCustomisationModule(self, isEvent: bool):
		"""
		If it's an event call, customisationModule should go last in line. If it's a message call, customisationModule should go first
		:param isEvent: bool
		"""

		if Customisation.MODULE_NAME not in self._modules.keys():
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


	def deactivateModule(self, moduleName: str):
		if moduleName in self._modules.keys():
			del self._modules[moduleName]


	def checkForModuleUpdates(self):
		if not managers.ConfigManager.getAliceConfigByName('moduleAutoUpdate'):
			return

		self._logger.info('[{}] Checking for module updates'.format(self.name))
		if not managers.InternetManager.online:
			self._logger.info('[{}] Not connected...'.format(self.name))
			return

		self._busyInstalling.set()

		availableModules = managers.ConfigManager.modulesConfigurations

		i = 0
		for moduleName in self._modules.keys():
			try:
				if moduleName not in availableModules.keys():
					continue

				req = requests.get('https://raw.githubusercontent.com/project-alice-powered-by-snips/ProjectAliceModules/master/PublishedModules/{}/{}/{}.install'.format(
					availableModules[moduleName]['author'],
					moduleName,
					moduleName
				))

				remoteFile = json.loads(req.content.decode())
				if float(remoteFile['version']) > float(availableModules[moduleName]['version']):
					with open(commons.rootDir() + '/system/moduleInstallTickets/' + moduleName + '.install', 'w') as ticket:
						json.dump(remoteFile, ticket)
					i += 1

			except Exception as e:
				self._logger.warning('[{}] Error checking updates for module "{}": {}'.format(self.name, moduleName, e))

		self._logger.info('[{}] Found {} module update(s)'.format(self.name, i))
		self._busyInstalling.clear()


	def _checkForModuleInstall(self):
		managers.ThreadManager.newTimer(interval = 10, func = self._checkForModuleInstall, autoStart = True)

		root = commons.rootDir() + '/system/moduleInstallTickets'
		files = fnmatch.filter(os.listdir(root), '*.install')

		if  self._busyInstalling.isSet() or \
			not managers.InternetManager.online or \
			len(files) <= 0 or \
			managers.ThreadManager.getLock('SnipsAssistantDownload').isSet():
			return

		if len(files) > 0:
			self._logger.info('[{}] Found {} install ticket(s)'.format(self.name, len(files)))
			self._busyInstalling.set()

			try:
				modulesToBoot = self._installModules(files)
			except:
				pass
			finally:
				if len(modulesToBoot) > 0:
					i = 1
					for moduleName, info in modulesToBoot.items():
						try:
							if i == len(modulesToBoot):
								managers.SamkillaManager.sync(moduleFilter=moduleName)
							else:
								managers.SamkillaManager.sync(moduleFilter=moduleName, download=False)
							i += 1
						except Exception as esamk:
							self._logger.error('[{}] Failed syncing with remote snips console {}'.format(self.name, esamk))

						self._modules = self._loadModuleList(moduleToLoad=moduleName, isUpdate=info['update'])

						try:
							managers.LanguageManager.loadStrings(moduleToLoad=moduleName)
							managers.TalkManager.loadTalks(moduleToLoad=moduleName)

							if info['update']:
								self._modules[moduleName]['instance'].onModuleUpdated()
							else:
								self._modules[moduleName]['instance'].onModuleInstalled()

							self._startModule(moduleInstance=self._modules[moduleName]['instance'])
							self._modules[moduleName]['instance'].onBooted()
						except Exception:
							pass

					managers.SnipsServicesManager.runCmd(cmd='restart')

				self._busyInstalling.clear()


	def _installModules(self, modules: list) -> dict:
		root = commons.rootDir() + '/system/moduleInstallTickets'
		availableModules = managers.ConfigManager.modulesConfigurations
		modulesToBoot = dict()
		managers.MqttServer.broadcast(topic='hermes/leds/systemUpdate')
		for file in modules:
			self._logger.info('[{}] Now taking care of module {}'.format(self.name, os.path.splitext(file)[0]))
			res = os.path.join(root, file)

			try:
				updating = False

				with open(res, 'r') as ticket:
					installFile = json.load(ticket)

				moduleName = installFile['name']
				path = os.path.join(installFile['author'], moduleName)

				if not moduleName:
					self._logger.error('[{}] Module name to install not found, aborting to avoid casualties!'.format(self.name))
					continue

				dirList:list = os.path.dirname(__file__).split('/')
				baseDir:str = '/'.join(dirList[:len(dirList) - 2])
				directory:str = baseDir + '/modules/' + moduleName

				if moduleName in availableModules.keys():
					localVersionDirExists: bool = os.path.isdir(directory)
					localVersionAttributeExists: bool = 'version' in availableModules[moduleName]

					localVersionIsLatest: bool = \
						localVersionDirExists and \
						localVersionAttributeExists and \
						float(availableModules[moduleName]['version']) >= float(installFile['version'])

					if localVersionIsLatest:
						self._logger.warning('[{}] Module "{}" is already installed, skipping'.format(self.name, moduleName))
						subprocess.run(['sudo', 'rm', res])
						continue
					else:
						self._logger.warning('[{}] Module "{}" needs updating'.format(self.name, moduleName))
						updating = True

				if moduleName in self._modules:
					try:
						self._modules[moduleName]['instance'].onStop()
					except Exception as e:
						self._logger.error('[{}] Error stopping "{}" for update: {}'.format(self.name, moduleName, e))

				gitCloner = GithubCloner(baseUrl = self.GITHUB_API_BASE_URL, path = path, dest = directory)

				if gitCloner.clone():
					self._logger.info('[{}] Module successfully downloaded'.format(self.name))
					try:
						if installFile['requirements']:
							for requirement in installFile['requirements']:
								subprocess.run(['./venv/bin/pip3.7', 'install', requirement])

						node = {
							"active": True,
							"version": installFile['version'],
							"author": installFile['author'],
							"conditions": installFile['conditions']
						}

						managers.ConfigManager.addModuleToAliceConfig(installFile['name'], node)
						subprocess.run(['mv', res, directory])
						modulesToBoot[moduleName] = {
							'update': updating
						}
					except Exception as e:
						self._logger.error('[{}] Failed installing module "{}": {}'.format(self.name, moduleName, e))
						os.remove(res)
				else:
					self._logger.error('[{}] Failed cloning module'.format(self.name))
					os.remove(res)

			except Exception as e:
				self._logger.error('[{}] Failed installing module "{}": {}'.format(self.name, moduleName, e))
				os.remove(res)

		managers.MqttServer.broadcast(topic='hermes/leds/clear')
		return modulesToBoot
