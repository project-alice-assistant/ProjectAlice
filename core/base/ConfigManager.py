import json
import subprocess
from pathlib import Path

import requests
import shutil

import configTemplate
from core.base.SkillManager import SkillManager
from core.base.model.GithubCloner import GithubCloner
from core.base.model.TomlFile import TomlFile
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
		constants.DEFAULT_SITE_ID = self._snipsConfigurations['snips-audio-server']['bind'].replace('@mqtt', '')


	def _loadCheckAndUpdateAliceConfigFile(self) -> dict:
		self.logInfo('Checking Alice configuration file')

		if not configFileExist:
			self.logInfo('Creating config file from config template')
			confs = {configName: configData['values'] if 'dataType' in configData and configData['dataType'] == 'list' else configData['defaultValue'] if 'defaultValue' in configData else configData for configName, configData in configTemplate.settings.items()}
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
			else:
				if setting == 'modules' or setting == 'supportedLanguages':
					continue

				if definition['dataType'] != 'list':
					if not isinstance(aliceConfigs[setting], type(definition['defaultValue'])):
						changes = True
						try:
							# First try to cast the seting we have to the new type
							aliceConfigs[setting] = type(definition['defaultValue'])(aliceConfigs[setting])
							self.logInfo(f'- Existing configuration type missmatch: {setting}, cast variable to template configuration type')
						except Exception:
							# If casting failed let's fall back to the new default value
							self.logInfo(f'- Existing configuration type missmatch: {setting}, replaced with template configuration')
							aliceConfigs[setting] = definition['defaultValue']
				else:
					values = definition['values'].values() if isinstance(definition['values'], dict) else definition['values']

					if aliceConfigs[setting] not in values:
						changes = True
						self.logInfo(f'- Selected value "{aliceConfigs[setting]}" for setting "{setting}" doesn\'t exist, reverted to default value "{definition["defaultValue"]}"')
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


	def addModuleToAliceConfig(self, skillName: str, data: dict):
		self._modulesConfigurations[skillName] = data
		self.updateAliceConfiguration('modules', self._modulesConfigurations)
		self.loadCheckAndUpdateModuleConfigurations(skillName)


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
		


	def updateModuleConfigurationFile(self, skillName: str, key: str, value: typing.Any):
		if skillName not in self._modulesConfigurations:
			self.logWarning(f'Was asked to update {key} in module {skillName} but module doesn\'t exist')
			return

		if key not in self._modulesConfigurations[skillName]:
			self.logWarning(f'Was asked to update {key} in module {skillName} but key doesn\'t exist')
			return

		self._modulesConfigurations[skillName][key] = value
		self._writeToModuleConfigurationFile(skillName, self._modulesConfigurations[skillName])


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
		for skillName, setting in modules.items():
			moduleCleaned = {key: value for key, value in setting.items() if key in misterProper}
			sort['modules'][skillName] = moduleCleaned

		self._aliceConfigurations = sort

		try:
			s = json.dumps(sort, indent=4).replace('false', 'False').replace('true', 'True')
			Path('config.py').write_text(f'settings = {s}')
			importlib.reload(config)
		except Exception:
			raise ConfigurationUpdateFailed()


	def _writeToModuleConfigurationFile(self, skillName: str, confs: dict):
		"""
		Saves the given configuration into config.py of the Module
		:param skillName: the targeted module
		:param confs: the dict to save
		"""

		# Don't store "active", "version", "author", "conditions" value in module config file
		misterProper = ['active', 'version', 'author', 'conditions']
		confsCleaned = {key: value for key, value in confs.items() if key not in misterProper}

		moduleConfigFile = Path(self.Commons.rootDir(), 'modules', skillName, 'config.json')
		moduleConfigFile.write_text(json.dumps(confsCleaned, indent=4))


	def loadSnipsConfigurations(self) -> TomlFile:
		self.logInfo('Loading Snips configuration file')

		snipsConfigPath = Path('/etc/snips.toml')
		snipsConfigTemplatePath = Path(self.Commons.rootDir(), 'system/snips/snips.toml')

		if not snipsConfigPath.exists():
			subprocess.run(['sudo', 'cp', snipsConfigTemplatePath, '/etc/snips.toml'])
			snipsConfigPath = snipsConfigTemplatePath

		snipsConfig = TomlFile.loadToml(snipsConfigPath)

		return snipsConfig


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
			self._snipsConfigurations.dump()

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
		if createIfNotExist and key not in self._snipsConfigurations[parent]:
			conf = self._snipsConfigurations[parent][key] # TomlFile does auto create missing keys
			self._snipsConfigurations.dump()
			return conf

		config = self._snipsConfigurations[parent].get(key, None)
		if config is None:
			self.logWarning(f'Tried to get "{parent}/{key}" in snips configuration but key was not found')

		return config


	def configAliceExists(self, configName: str) -> bool:
		return configName in self._aliceConfigurations


	def configModuleExists(self, configName: str, skillName: str) -> bool:
		return skillName in self._modulesConfigurations and configName in self._modulesConfigurations[skillName]


	def getAliceConfigByName(self, configName: str, voiceControl: bool = False) -> typing.Any:
		return self._aliceConfigurations.get(
			configName,
			difflib.get_close_matches(word=configName, possibilities=self._aliceConfigurations, n=3) if voiceControl else ''
		)


	def getModuleConfigByName(self, skillName: str, configName: str) -> typing.Any:
		return self._modulesConfigurations.get(skillName, dict()).get(configName, None)


	def getModuleConfigs(self, skillName: str) -> dict:
		return self._modulesConfigurations.get(skillName, dict())


	def getModuleConfigsTemplateByName(self, skillName: str, configName: str) -> typing.Any:
		return self._modulesTemplateConfigurations.get(skillName, dict()).get(configName, None)


	def getModuleConfigsTemplate(self, skillName: str) -> dict:
		return self._modulesTemplateConfigurations.get(skillName, dict())


	def loadCheckAndUpdateModuleConfigurations(self, module: str = None):
		modulesConfigurations = dict()

		modulesPath = Path(self.Commons.rootDir() + '/modules')
		for moduleDirectory in modulesPath.glob('*'):
			if not moduleDirectory.is_dir() or (module is not None and moduleDirectory.stem != module) or moduleDirectory.stem.startswith('_'):
				continue

			self.logInfo(f'Checking configuration for module {moduleDirectory.stem}')

			moduleConfigFile = Path(modulesPath / moduleDirectory / 'config.json')
			moduleConfigTemplate = Path(modulesPath / moduleDirectory / 'config.json.template')
			skillName = moduleDirectory.stem
			config = dict()

			if not moduleConfigFile.exists() and moduleConfigTemplate.exists():
				self._newModuleConfigFile(skillName, moduleConfigTemplate)

			elif moduleConfigFile.exists() and not moduleConfigTemplate.exists():
				self.logInfo(f'- Deprecated config file for module "{skillName}", removing')
				moduleConfigFile.unlink()
				self._modulesTemplateConfigurations[skillName] = dict()
				modulesConfigurations[skillName] = dict()

			elif moduleConfigFile.exists() and moduleConfigTemplate.exists():
				config = json.load(moduleConfigFile.open())
				configSample = json.load(moduleConfigTemplate.open())
				self._modulesTemplateConfigurations[skillName] = configSample

				try:
					changes = False
					for setting, definition in configSample.items():
						if setting not in config:
							self.logInfo(f'- New configuration found for module "{skillName}": {setting}')
							changes = True
							config[setting] = definition['defaultValue']

						elif 'defaultValue' in definition and not isinstance(config[setting], type(definition['defaultValue'])):
							changes = True
							try:
								# First try to cast the seting we have to the new type
								config[setting] = type(definition['defaultValue'])(config[setting])
								self.logInfo(f'- Existing configuration type missmatch for module "{skillName}": {setting}, cast variable to template configuration type')
							except Exception:
								# If casting failed let's fall back to the new default value
								self.logInfo(f'- Existing configuration type missmatch for module "{skillName}": {setting}, replaced with template configuration')
								config[setting] = definition['defaultValue']

					temp = config.copy()
					for k, v in temp.items():
						if k not in configSample:
							self.logInfo(f'- Deprecated configuration for module "{skillName}": {k}')
							changes = True
							del config[k]

					if changes:
						self._writeToModuleConfigurationFile(skillName, config)
				except Exception as e:
					self.logWarning(f'- Failed updating existing module config file for module {skillName}: {e}')
					moduleConfigFile.unlink()
					if moduleConfigTemplate.exists():
						self._newModuleConfigFile(skillName, moduleConfigTemplate)
					else:
						self.logWarning(f'- Cannot create config, template not existing, skipping module')

			else:
				self._modulesTemplateConfigurations[skillName] = dict()
				modulesConfigurations[skillName] = dict()

			if skillName in self._aliceConfigurations['modules']:
				config = {**config, **self._aliceConfigurations['modules'][skillName]}
			else:
				# For some reason we have a module not declared in alice configs... I think getting rid of it is best
				if skillName not in SkillManager.NEEDED_SKILLS:
					self.logInfo('- Module not declared in config but files are existing, cleaning up')
					shutil.rmtree(moduleDirectory, ignore_errors=True)
					if skillName in modulesConfigurations:
						modulesConfigurations.pop(skillName)
					continue
				else:
					self.logInfo(f'- Module is required but is missing definition in Alice config, generating them')
					try:
						installFile = json.load(Path(modulesPath / moduleDirectory / f'{skillName}.install').open())
						node = {
							'active'    : True,
							'version'   : installFile['version'],
							'author'    : installFile['author'],
							'conditions': installFile['conditions']
						}
						config = {**config, **node}
						self._modulesConfigurations[skillName] = config
						self.updateAliceConfiguration('modules', self._modulesConfigurations)
					except Exception as e:
						self.logError(f'- Failed generating default config, scheduling download: {e}')
						subprocess.run(['wget', f'http://modules.projectalice.ch/{skillName}', '-O', Path(self.Commons.rootDir(), f'system/moduleInstallTickets/{skillName}.install')])
						if skillName in modulesConfigurations:
							modulesConfigurations.pop(skillName)
						continue

			if config:
				modulesConfigurations[skillName] = config

		self._modulesConfigurations = {**self._modulesConfigurations, **modulesConfigurations}


	def _newModuleConfigFile(self, skillName: str, moduleConfigTemplate: Path):
		self.logInfo(f'- New config file for module "{skillName}", creating from template')

		template = json.load(moduleConfigTemplate.open())

		confs = {configName: configData['defaultValue'] if 'defaultValue' in configData else configData for configName, configData in template.items()}
		self._modulesTemplateConfigurations[skillName] = template
		self._modulesConfigurations[skillName] = confs
		self._writeToModuleConfigurationFile(skillName, confs)


	def deactivateSkill(self, skillName: str, persistent: bool = False):

		if skillName in self.aliceConfigurations['modules']:
			self.logInfo(f"Deactivated skill {skillName} {'with' if persistent else 'without'} persistence")
			self.aliceConfigurations['modules'][skillName]['active'] = False

			if persistent:
				self.writeToAliceConfigurationFile(self._aliceConfigurations)


	def activateModule(self, skillName: str, persistent: bool = False):

		if skillName in self.aliceConfigurations['modules']:
			self.logInfo(f"Activated module {skillName} {'with' if persistent else 'without'} persistence")
			self.aliceConfigurations['modules'][skillName]['active'] = True

			if persistent:
				self.writeToAliceConfigurationFile(self._aliceConfigurations)


	def removeModule(self, skillName: str):
		if skillName in self.aliceConfigurations['modules']:
			modules = self.aliceConfigurations['modules']
			del modules[skillName]
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


	def getSkillsUpdateSource(self) -> str:
		updateSource = 'master'
		if self.getAliceConfigByName('updateChannel') == 'master':
			return updateSource

		req = requests.get('https://api.github.com/repos/project-alice-assistant/ProjectAliceModules/branches', auth=GithubCloner.getGithubAuth())
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
	def snipsConfigurations(self) -> TomlFile:
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
