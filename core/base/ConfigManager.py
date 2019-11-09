import json
from pathlib import Path

import requests
import shutil

import configTemplate
from core.base.SuperManager import SuperManager
from core.base.model.GithubCloner import GithubCloner
from core.base.model.Version import Version

try:
	# noinspection PyUnresolvedReferences,PyPackageRequirements
	import config
	configFileExist = True
except ModuleNotFoundError:
	configFileNotExist = False

import difflib
import importlib
import typing
import toml
from core.ProjectAliceExceptions import ConfigurationUpdateFailed, VitalConfigMissing
from core.base.model.Manager import Manager
from core.commons import constants


class ConfigManager(Manager):

	NAME = 'ConfigManager'

	def __init__(self):
		super().__init__(self.NAME)

		self._aliceModuleConfigurationKeys = [
			'active',
			'version',
			'author',
			'conditions'
		]

		self._vitalConfigs = [
			'intentsOwner',
			'snipsConsoleLogin',
			'snipsConsolePassword'
		]

		self._aliceConfigurations: typing.Dict[str, typing.Any] = self._loadCheckAndUpdateAliceConfigFile()
		self._aliceTemplateConfigurations: typing.Dict[str, dict] = configTemplate.settings
		self._snipsConfigurations = self.loadSnipsConfigurations()
		self._setDefaultSiteId()

		self._modulesConfigurations = dict()
		self._modulesTemplateConfigurations: typing.Dict[str, dict] = dict()
		self.loadCheckAndUpdateModuleConfigurations()


	def onStart(self):
		super().onStart()
		for conf in self._vitalConfigs:
			if conf not in self._aliceConfigurations or self._aliceConfigurations[conf] == '':
				raise VitalConfigMissing(conf)


	def _setDefaultSiteId(self):
		constants.DEFAULT_SITE_ID = self._snipsConfigurations.get('snips-audio-server', {'bind': 'default@mqtt'}).get('bind', 'default@mqtt').replace('@mqtt', '')


	def _loadCheckAndUpdateAliceConfigFile(self) -> dict:
		self.logInfo('Checking Alice configuration file')

		if not configFileExist:
			self.logInfo('Creating config file from config template')
			confs = {configName: configData['defaultValue'] if 'defaultValue' in configData else configData for configName, configData in configTemplate.settings.items()}
			Path('config.py').write_text(f'settings = {json.dumps(confs, indent=4)}')
			aliceConfigs = importlib.import_module('config.py').settings.copy()
		else:
			aliceConfigs = config.settings.copy()

		changes = False
		for setting, definition in configTemplate.settings.items():
			if setting not in aliceConfigs:
				self.logInfo(f'- New configuration found: {setting}')
				changes = True
				aliceConfigs[setting] = definition['defaultValue']
			elif 'defaultValue' in definition and not isinstance(aliceConfigs[setting], type(definition['defaultValue'])):
				changes = True
				try:
					# First try to cast the seting we have to the new type
					aliceConfigs[setting] = type(definition['defaultValue'])(aliceConfigs[setting])
					self.logInfo(f'- Existing configuration type missmatch: {setting}, cast variable to template configuration type')
				except Exception:
					# If casting failed let's fall back to the new default value
					self.logInfo(f'- Existing configuration type missmatch: {setting}, replaced with template configuration')
					aliceConfigs[setting] = definition['defaultValue']

		temp = aliceConfigs.copy()

		for k, v in temp.items():
			if k not in configTemplate.settings:
				self.logInfo(f'- Deprecated configuration: {k}')
				changes = True
				del aliceConfigs[k]

		if changes:
			self.writeToAliceConfigurationFile(aliceConfigs)

		return aliceConfigs


	def addModuleToAliceConfig(self, moduleName: str, data: dict):
		self._modulesConfigurations[moduleName] = {**self._modulesConfigurations[moduleName], **data} if moduleName in self._modulesConfigurations else data
		self.updateAliceConfiguration('modules', self._modulesConfigurations)
		self.loadCheckAndUpdateModuleConfigurations(moduleName)


	def updateAliceConfiguration(self, key: str, value: typing.Any):
		if key not in self._aliceConfigurations:
			self.logWarning(f'Was asked to update {key} but key doesn\'t exist')
			raise ConfigurationUpdateFailed()
		
		try:
			# Remove module configurations
			if key == 'modules':
				value = {k: v for k, v in value.items() if k not in self._aliceModuleConfigurationKeys}
		except AttributeError:
			raise ConfigurationUpdateFailed()

		self._aliceConfigurations[key] = value
		self.writeToAliceConfigurationFile(self.aliceConfigurations)
		


	def updateModuleConfigurationFile(self, moduleName: str, key: str, value: typing.Any):
		if moduleName not in self._modulesConfigurations:
			self.logWarning(f'Was asked to update {key} in module {moduleName} but module doesn\'t exist')
			return

		if key not in self._modulesConfigurations[moduleName]:
			self.logWarning(f'Was asked to update {key} in module {moduleName} but key doesn\'t exist')
			return

		self._modulesConfigurations[moduleName][key] = value
		self._writeToModuleConfigurationFile(moduleName, self._modulesConfigurations[moduleName])


	def writeToAliceConfigurationFile(self, confs: dict):
		"""
		Saves the given configuration into config.py
		:param confs: the dict to save
		"""
		sort = dict(sorted(confs.items()))

		# Only store "active", "version", "author", "conditions" value for module config
		misterProper = ['active', 'version', 'author', 'conditions']

		# pop modules key so it gets added in the back
		modules = sort.pop('modules')

		sort['modules'] = dict()
		for moduleName, setting in modules.items():
			moduleCleaned = {key: value for key, value in setting.items() if key in misterProper}
			sort['modules'][moduleName] = moduleCleaned

		self._aliceConfigurations = sort

		try:
			s = json.dumps(sort, indent=4).replace('false', 'False').replace('true', 'True')
			Path('config.py').write_text(f'settings = {s}')
			importlib.reload(config)
		except Exception:
			raise ConfigurationUpdateFailed()


	def _writeToModuleConfigurationFile(self, moduleName: str, confs: dict):
		"""
		Saves the given configuration into config.py of the Module
		:param moduleName: the targeted module
		:param confs: the dict to save
		"""

		# Don't store "active", "version", "author", "conditions" value in module config file
		misterProper = ['active', 'version', 'author', 'conditions']
		confsCleaned = {key: value for key, value in confs.items() if key not in misterProper}

		moduleConfigFile = Path(self.Commons.rootDir(), 'modules', moduleName, 'config.json')
		moduleConfigFile.write_text(json.dumps(confsCleaned, indent=4))


	def loadSnipsConfigurations(self) -> dict:
		self.logInfo('Loading Snips configuration file')
		snipsConfig = Path('/etc/snips.toml')
		if snipsConfig.exists():
			return toml.loads(snipsConfig.read_text())
		else:
			self.logError('Failed retrieving Snips configs')
			SuperManager.getInstance().onStop()


	def updateSnipsConfiguration(self, parent: str, key: str, value, restartSnips: bool = False, createIfNotExist: bool = True):
		"""
		Setting a config in snips.toml
		:param parent: Parent key in toml
		:param key: Key in that parent key
		:param value: The value to set
		:param restartSnips: Whether to restart Snips or not after changing the value
		:param createIfNotExist: If the parent key or the key doesn't exist do create it
		"""

		config = self.getSnipsConfiguration(parent=parent, key=key, createIfNotExist=createIfNotExist)
		if config is not None:
			self._snipsConfigurations[parent][key] = value

			Path('/etc/snips.toml').write_text(toml.dumps(self._snipsConfigurations))

			if restartSnips:
				self.SnipsServicesManager.runCmd('restart')


	def getSnipsConfiguration(self, parent: str, key: str, createIfNotExist: bool = True) -> typing.Optional[str]:
		"""
		Getting a specific configuration from snips.toml
		:param parent: parent key
		:param key: key within parent conf
		:param createIfNotExist: If that conf doesn't exist, create it
		:return: config value
		"""
		if createIfNotExist:
			self._snipsConfigurations[parent] = self._snipsConfigurations.get(parent, dict())
			self._snipsConfigurations[parent][key] = self._snipsConfigurations[parent].get(key, '')

		config = self._snipsConfigurations.get(parent, dict()).get(key, None)
		if config is None:
			self.logWarning(f'Tried to get "{parent}/{key}" in snips configuration but key was not found')

		return config


	def configAliceExists(self, configName: str) -> bool:
		return configName in self._aliceConfigurations


	def configModuleExists(self, configName: str, moduleName: str) -> bool:
		return moduleName in self._modulesConfigurations and configName in self._modulesConfigurations[moduleName]


	def getAliceConfigByName(self, configName: str, voiceControl: bool = False) -> typing.Any:
		return self._aliceConfigurations.get(
			configName,
			difflib.get_close_matches(word=configName, possibilities=self._aliceConfigurations, n=3) if voiceControl else ''
		)


	def getModuleConfigByName(self, moduleName: str, configName: str) -> typing.Any:
		return self._modulesConfigurations.get(moduleName, dict()).get(configName, None)


	def getModuleConfigs(self, moduleName: str) -> dict:
		return self._modulesConfigurations.get(moduleName, dict())


	def getModuleConfigsTemplateByName(self, moduleName: str, configName: str) -> typing.Any:
		return self._modulesTemplateConfigurations.get(moduleName, dict()).get(configName, None)


	def getModuleConfigsTemplate(self, moduleName: str) -> dict:
		return self._modulesTemplateConfigurations.get(moduleName, dict())


	def loadCheckAndUpdateModuleConfigurations(self, module: str = None):
		modulesConfigurations = dict()

		modulesPath = Path(self.Commons.rootDir() + '/modules')
		for moduleDirectory in modulesPath.glob('*'):
			if not moduleDirectory.is_dir() or (module is not None and moduleDirectory.stem != module) or moduleDirectory.stem.startswith('_'):
				continue

			self.logInfo(f'Checking configuration for module {moduleDirectory.stem}')

			moduleConfigFile = Path(modulesPath / moduleDirectory / 'config.json')
			moduleConfigTemplate = Path(modulesPath / moduleDirectory / 'config.json.template')
			moduleName = moduleDirectory.stem
			config = dict()

			if not moduleConfigFile.exists() and moduleConfigTemplate.exists():
				self._newModuleConfigFile(moduleName, moduleConfigTemplate)

			elif moduleConfigFile.exists() and not moduleConfigTemplate.exists():
				self.logInfo(f'- Deprecated config file for module "{moduleName}", removing')
				moduleConfigFile.unlink()
				self._modulesTemplateConfigurations[moduleName] = dict()
				modulesConfigurations[moduleName] = dict()

			elif moduleConfigFile.exists() and moduleConfigTemplate.exists():
				config = json.load(moduleConfigFile.open())
				configSample = json.load(moduleConfigTemplate.open())
				self._modulesTemplateConfigurations[moduleName] = configSample

				try:
					changes = False
					for setting, definition in configSample.items():
						if setting not in config:
							self.logInfo(f'- New configuration found for module "{moduleName}": {setting}')
							changes = True
							config[setting] = definition['defaultValue']

						elif 'defaultValue' in definition and not isinstance(config[setting], type(definition['defaultValue'])):
							changes = True
							try:
								# First try to cast the seting we have to the new type
								config[setting] = type(definition['defaultValue'])(config[setting])
								self.logInfo(f'- Existing configuration type missmatch for module "{moduleName}": {setting}, cast variable to template configuration type')
							except Exception:
								# If casting failed let's fall back to the new default value
								self.logInfo(f'- Existing configuration type missmatch for module "{moduleName}": {setting}, replaced with template configuration')
								config[setting] = definition['defaultValue']

					temp = config.copy()
					for k, v in temp.items():
						if k not in configSample:
							self.logInfo(f'- Deprecated configuration for module "{moduleName}": {k}')
							changes = True
							del config[k]

					if changes:
						self._writeToModuleConfigurationFile(moduleName, config)
				except Exception as e:
					self.logWarning(f'- Failed updating existing module config file for module {moduleName}: {e}')
					moduleConfigFile.unlink()
					if moduleConfigTemplate.exists():
						self._newModuleConfigFile(moduleName, moduleConfigTemplate)
					else:
						self.logWarning(f'- Cannot create config, template not existing, skipping module')

			else:
				self._modulesTemplateConfigurations[moduleName] = dict()
				modulesConfigurations[moduleName] = dict()

			if moduleName in self._aliceConfigurations['modules']:
				config = {**config, **self._aliceConfigurations['modules'][moduleName]}
			else:
				# For some reason we have a module not declared in alice configs... I think getting rid of it is best
				self.logInfo(f'Module "{moduleName}" is not declared in config but files are existing, cleaning up')
				shutil.rmtree(moduleDirectory, ignore_errors=True)
				continue

			# TODO decide what's best
			# Or generate its infos?
			# self.logInfo(f'Missing module declaration in Alice config file for module {moduleName}')
			# installFile = json.load(Path(modulesPath / moduleDirectory / f'{moduleName}.install').open())
			# node = {
			# 	'active'    : False,
			# 	'version'   : installFile['version'],
			# 	'author'    : installFile['author'],
			# 	'conditions': installFile['conditions']
			# }
			# self._modulesConfigurations[moduleName] = {**config, **node}
			# self.updateAliceConfiguration('modules', self._modulesConfigurations)

			modulesConfigurations[moduleName] = config

		self._modulesConfigurations = modulesConfigurations


	def _newModuleConfigFile(self, moduleName: str, moduleConfigTemplate: Path):
		self.logInfo(f'- New config file for module "{moduleName}", creating from template')

		template = json.load(moduleConfigTemplate.open())

		confs = {configName: configData['defaultValue'] if 'defaultValue' in configData else configData for configName, configData in template.items()}
		self._modulesTemplateConfigurations[moduleName] = template
		self._writeToModuleConfigurationFile(moduleName, confs)


	def deactivateModule(self, moduleName: str, persistent: bool = False):

		if moduleName in self.aliceConfigurations['modules']:
			self.logInfo(f"Deactivated module {moduleName} {'with' if persistent else 'without'} persistence")
			self.aliceConfigurations['modules'][moduleName]['active'] = False

			if persistent:
				self.writeToAliceConfigurationFile(self._aliceConfigurations)


	def activateModule(self, moduleName: str, persistent: bool = False):

		if moduleName in self.aliceConfigurations['modules']:
			self.logInfo(f"Activated module {moduleName} {'with' if persistent else 'without'} persistence")
			self.aliceConfigurations['modules'][moduleName]['active'] = True

			if persistent:
				self.writeToAliceConfigurationFile(self._aliceConfigurations)


	def removeModule(self, moduleName: str):
		if moduleName in self.aliceConfigurations['modules']:
			modules = self.aliceConfigurations['modules']
			modules.pop(moduleName)
			self.aliceConfigurations['modules'] = modules
			self.writeToAliceConfigurationFile(self._aliceConfigurations)


	def changeActiveLanguage(self, toLang: str):
		if toLang in self.getAliceConfigByName('supportedLanguages'):
			self.updateAliceConfiguration('activeLanguage', toLang)
			return True
		return False


	def changeActiveSnipsProjectIdForLanguage(self, projectId: str, forLang: str):
		langConfig = self.getAliceConfigByName('supportedLanguages').copy()

		if forLang in langConfig:
			langConfig[forLang]['snipsProjectId'] = projectId

		self.updateAliceConfiguration('supportedLanguages', langConfig)


	def getAliceConfigType(self, confName: str) -> typing.Optional[str]:
		# noinspection PyTypeChecker
		return self._aliceConfigurations.get(confName['dataType'], None)


	def isAliceConfHidden(self, confName: str) -> bool:
		return confName in self._aliceTemplateConfigurations and \
			self._aliceTemplateConfigurations.get('display') == 'hidden'


	def getModulesUpdateSource(self) -> str:
		updateSource = 'master'
		if self.getAliceConfigByName('updateChannel') == 'master':
			return updateSource

		req = requests.get('https://api.github.com/repos/project-alice-powered-by-snips/ProjectAliceModules/branches', auth=GithubCloner.getGithubAuth())
		result = req.json()
		if result:
			userUpdatePref = self.getAliceConfigByName('updateChannel')
			versions = list()
			for branch in result:
				repoVersion = Version(branch['name'])
				if not repoVersion.isVersionNumber:
					continue

				if userUpdatePref == 'alpha' and repoVersion.infos['releaseType'] in ('master', 'rc', 'b', 'a'):
					versions.append(repoVersion)
				elif userUpdatePref == 'beta' and repoVersion.infos['releaseType'] in ('master', 'rc', 'b'):
					versions.append(repoVersion)
				elif userUpdatePref == 'rc' and repoVersion.infos['releaseType'] in ('master', 'rc'):
					versions.append(repoVersion)

			if len(versions) > 0:
				versions.sort(reverse=True)
				updateSource = versions[0]

		return updateSource


	@property
	def snipsConfigurations(self) -> dict:
		return self._snipsConfigurations


	@property
	def aliceConfigurations(self) -> dict:
		return self._aliceConfigurations


	@property
	def modulesConfigurations(self) -> dict:
		return self._modulesConfigurations


	@property
	def vitalConfigs(self) -> list:
		return self._vitalConfigs


	@property
	def aliceModuleConfigurationKeys(self) -> list:
		return self._aliceModuleConfigurationKeys


	@property
	def aliceTemplateConfigurations(self) -> dict:
		return self._aliceTemplateConfigurations
