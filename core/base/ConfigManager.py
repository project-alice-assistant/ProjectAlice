import shutil

from core.base.SuperManager import SuperManager

try:
	# noinspection PyUnresolvedReferences
	import config
except ModuleNotFoundError:
	shutil.copyfile('configSample.py', 'config.py')
	print('Created config file from config samples')
	# noinspection PyUnresolvedReferences
	import config

import difflib
import importlib
import json
from pathlib import Path
import typing
import toml

import configSample
from core.ProjectAliceExceptions import ConfigurationUpdateFailed, VitalConfigMissing
from core.base.model.Manager import Manager
from core.commons import commons, constants


class ConfigManager(Manager):

	NAME = 'ConfigManager'

	def __init__(self):
		super().__init__(self.NAME)
		self._snipsConfigurations 		= dict()
		self._aliceConfigurations 		= config.settings
		self._modulesConfigurations 	= dict()

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

		self._checkAndUpdateAliceConfigFile()
		self.loadSnipsConfigurations()
		self._setDefaultSiteId()

		self.loadModuleConfigurations()
		self._checkAndUpdateModuleConfigFiles()


	def onStart(self):
		super().onStart()
		for conf in self._vitalConfigs:
			if conf not in self._aliceConfigurations or self._aliceConfigurations[conf] == '':
				raise VitalConfigMissing()


	def _setDefaultSiteId(self):
		constants.DEFAULT_SITE_ID = self._snipsConfigurations.get('snips-audio-server', {'bind': 'default'}).get('bind', 'default')


	def _checkAndUpdateAliceConfigFile(self):
		self._logger.info('[{}] Checking Alice configuration file'.format(self.name))

		changes = False

		availableConfigs = config.settings.copy()

		for k, v in configSample.settings.items():
			if k not in availableConfigs:
				self._logger.info('- New configuration found: {}'.format(k))
				changes = True
				availableConfigs[k] = v
			elif type(availableConfigs[k]) != type(v):
				self._logger.info('- Existing configuration type missmatch: {}, replaced with sample configuration'.format(k))
				changes = True
				availableConfigs[k] = v

		temp = availableConfigs.copy()

		for k, v in temp.items():
			if k not in configSample.settings:
				self._logger.info('- Deprecated configuration: {}'.format(k))
				changes = True
				del availableConfigs[k]

		if changes:
			self._writeToAliceConfigurationFile(availableConfigs)


	def addModuleToAliceConfig(self, moduleName: str, data: dict):
		self._modulesConfigurations[moduleName] = {**self._modulesConfigurations[moduleName], **data} if moduleName in self._modulesConfigurations else data
		self.updateAliceConfiguration('modules', self._modulesConfigurations)
		self._checkAndUpdateModuleConfigFiles(moduleName)
		self.loadModuleConfigurations(moduleName)


	def updateAliceConfiguration(self, key: str, value: typing.Any):
		try:
			if key not in self._aliceConfigurations:
				self._logger.warning('[{}] Was asked to update {} but key doesn\'t exist'.format(self.name, key))
				raise Exception

			#Remove module configurations
			if key == 'modules':
				value = dict((k, v) for k, v in value.items() if k not in self._aliceModuleConfigurationKeys)

			self._aliceConfigurations[key] = value
			self._writeToAliceConfigurationFile(self.aliceConfigurations)
		except Exception as e:
			raise ConfigurationUpdateFailed(e)


	def updateModuleConfigurationFile(self, moduleName: str, key: str, value: typing.Any):
		if moduleName not in self._modulesConfigurations:
			self._logger.warning('[{}] Was asked to update {} in module {} but module doesn\'t exist'.format(self.name, key, moduleName))
			return

		if key not in self._modulesConfigurations[moduleName]:
			self._logger.warning('[{}] Was asked to update {} in module {} but key doesn\'t exist'.format(self.name, key, moduleName))
			return

		self._modulesConfigurations[moduleName][key] = value
		self._writeToModuleConfigurationFile(moduleName, self._modulesConfigurations[moduleName])


	@staticmethod
	def _writeToAliceConfigurationFile(confs: dict):
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
		for moduleName, conf in modules.items():
			moduleCleaned = {key: value for key, value in conf.items() if key in misterProper}
			sort['modules'][moduleName] = moduleCleaned

		try:
			s = json.dumps(sort, indent=4).replace('false', 'False').replace('true', 'True')
			Path('config.py').write_text('settings = {}'.format(s))
			importlib.reload(config)
		except Exception as e:
			raise ConfigurationUpdateFailed(e)


	@staticmethod
	def _writeToModuleConfigurationFile(moduleName: str, confs: dict):
		"""
		Saaves the given configuration into config.py of the Module
		:param moduleName: the targeted module
		:param confs: the dict to save
		"""

		# Don't store "active", "version", "author", "conditions" value in module config file
		misterProper = ['active', 'version', 'author', 'conditions']
		confsCleaned = {key: value for key, value in confs.items() if key not in misterProper}

		moduleConfigFile = Path(commons.rootDir(), 'modules', moduleName, 'config.json')
		moduleConfigFile.write_text(json.dumps(confsCleaned, indent=4))


	def loadSnipsConfigurations(self):
		self._logger.info('[{}] Loading Snips configuration file'.format(self.name))
		snipsConfig = Path('/etc/snips.toml')
		if snipsConfig.exists():
			self._snipsConfigurations = toml.loads(snipsConfig.read_text())
		else:
			self._logger.error('Failed retrieving Snips configs')
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
		if config is not None and config != value:
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
			self._logger.warning('Tried to get "{}/{}" in snips configuration but key was not found'.format(parent, key))

		return config


	def configAliceExists(self, configName: str) -> bool:
		return configName in self._aliceConfigurations


	def configModuleExists(self, configName: str, moduleName: str) -> bool:
		return moduleName in self._modulesConfigurations and configName in self._modulesConfigurations[moduleName]


	def getAliceConfigByName(self, configName: str, voiceControl: bool = False) -> dict:
		return self._aliceConfigurations.get(
			configName,
			difflib.get_close_matches(word=configName, possibilities=self._aliceConfigurations, n=3) if voiceControl else dict()
		)


	def getModuleConfigs(self, moduleName: str) -> dict:
		return self.getModuleConfigByName(moduleName, constants.ALL)


	def getModuleConfigByName(self, moduleName: str, configName: str, voiceControl: bool = False) -> dict:
		if moduleName not in self._modulesConfigurations:
			return dict()

		if configName == constants.ALL:
			return self._modulesConfigurations[moduleName]

		return self._modulesConfigurations[moduleName].get(
			configName,
			difflib.get_close_matches(word=configName, possibilities=self._modulesConfigurations[moduleName], n=3) if voiceControl else dict()
		)


	def _checkAndUpdateModuleConfigFiles(self, module: str = ''):
		self._logger.info('[{}] Checking module configuration files'.format(self.name))

		# Iterate through all modules declared in global config file
		for moduleName in self._modulesConfigurations:
			if module and moduleName != module:
				continue

			if not self._modulesConfigurations[moduleName]['active']:
				continue

			changes = False

			moduleConfigFile = Path(commons.rootDir(), 'modules', moduleName, 'config.json')
			moduleConfigFileExists = moduleConfigFile.exists()
			moduleConfigFileTemplate = moduleConfigFile.with_suffix(moduleConfigFile.suffix + '.dist')
			moduleConfigFileTemplateExists = moduleConfigFileTemplate.exists()

			if not moduleConfigFileTemplateExists and not moduleConfigFileExists:
				continue

			# If no conf template found but there's a conf file available
			if not moduleConfigFileTemplateExists and moduleConfigFileExists:
				# Delete it
				moduleConfigFile.unlink()
				self._logger.info('- Deprecated module config file found for module {}'.format(moduleName))
				continue

			# Use dist (aka default config file) to generate a genuine config file if needed
			if moduleConfigFileTemplateExists and not moduleConfigFileExists:
				shutil.copyfile(moduleConfigFileTemplate, moduleConfigFile)
				self._logger.info('- New config file setup for module {}'.format(moduleName))
				continue

			# The final case is if moduleConfigFileTemplateExists and moduleConfigFileExists
			with open(moduleConfigFileTemplate) as jsonDataFile:
				configTemplate = json.load(jsonDataFile)

				for k, v in configTemplate.items():
					if k not in self._modulesConfigurations[moduleName]:
						self._logger.info('- New module configuration found: {} for module {}'.format(k, moduleName))
						changes = True
						self._modulesConfigurations[moduleName][k] = v
					elif type(self._modulesConfigurations[moduleName][k]) != type(v):
						self._logger.info('- Existing module configuration type missmatch: {}, replaced with sample configuration for module {}'.format(k, moduleName))
						changes = True
						self._modulesConfigurations[moduleName][k] = v

			temp = self._modulesConfigurations[moduleName].copy()

			for k, v in temp.items():
				if k == 'active':
					continue

				if k not in configTemplate and k not in self._aliceModuleConfigurationKeys:
					self._logger.info('- Deprecated module configuration: "{}" for module "{}"'.format(k, moduleName))
					changes = True
					del self._modulesConfigurations[moduleName][k]

			if changes:
				self._writeToModuleConfigurationFile(moduleName, self.modulesConfigurations[moduleName])


	def loadModuleConfigurations(self, module: str = ''):
		self._logger.info('[{}] Loading module configurations'.format(self.name))

		# Iterate through all modules declared in global config file
		for moduleName in self._aliceConfigurations['modules']:

			if module and moduleName != module:
				continue

			moduleConfigFile = Path(commons.rootDir(), 'modules', moduleName, 'config.json')
			moduleConfigFileExists = moduleConfigFile.exists()

			if not self._aliceConfigurations['modules'][moduleName]['active'] or not moduleConfigFileExists:
				self._modulesConfigurations[moduleName] = {**self._aliceConfigurations['modules'][moduleName]}
				continue

			try:
				self._logger.info('- Loading config file for module {}'.format(moduleName))
				with open(moduleConfigFile) as jsonFile:
					self._modulesConfigurations[moduleName] = {**json.load(jsonFile), **self._aliceConfigurations['modules'][moduleName]}

			except json.decoder.JSONDecodeError:
				self._logger.error('- Error in config file for module {}'.format(moduleName))


	def deactivateModule(self, moduleName: str, persistent: bool = False):

		if moduleName in self.aliceConfigurations['modules']:
			self._logger.info('[{}] Deactivated module {} {} persistence'.format(self.name, moduleName, 'with' if persistent else 'without'))
			self.aliceConfigurations['modules'][moduleName]['active'] = False

			if persistent:
				self._writeToAliceConfigurationFile(self._aliceConfigurations)


	def activateModule(self, moduleName: str, persistent: bool = False):

		if moduleName in self.aliceConfigurations['modules']:
			self._logger.info('[{}] Activated module {} {} persistence'.format(self.name, moduleName, 'with' if persistent else 'without'))
			self.aliceConfigurations['modules'][moduleName]['active'] = True

			if persistent:
				self._writeToAliceConfigurationFile(self._aliceConfigurations)


	def removeModule(self, moduleName: str):
		if moduleName in self.aliceConfigurations['modules']:
			modules = self.aliceConfigurations['modules']
			modules.pop(moduleName)
			self.aliceConfigurations['modules'] = modules
			self._writeToAliceConfigurationFile(self._aliceConfigurations)


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
