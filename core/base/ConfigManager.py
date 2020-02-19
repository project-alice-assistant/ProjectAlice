import json
import logging
from pathlib import Path

import shutil

import configTemplate
from core.base.SkillManager import SkillManager
from core.base.model.TomlFile import TomlFile

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

	def __init__(self):
		super().__init__()

		self._aliceSkillConfigurationKeys = [
			'active',
			'version',
			'author',
			'conditions'
		]

		self._vitalConfigs = [
			'intentsOwner'
		]

		self._aliceConfigurations: typing.Dict[str, typing.Any] = self._loadCheckAndUpdateAliceConfigFile()
		self._aliceTemplateConfigurations: typing.Dict[str, dict] = configTemplate.settings
		self._snipsConfigurations = self.loadSnipsConfigurations()
		self._setDefaultSiteId()

		self._skillsConfigurations = dict()
		self._skillsTemplateConfigurations: typing.Dict[str, dict] = dict()
		self.loadCheckAndUpdateSkillConfigurations()


	def onStart(self):
		super().onStart()
		for conf in self._vitalConfigs:
			if conf not in self._aliceConfigurations or self._aliceConfigurations[conf] == '':
				raise VitalConfigMissing(conf)


	def _setDefaultSiteId(self):
		if self._snipsConfigurations['snips-audio-server']['bind']:
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
				aliceConfigs[setting] = definition.get('defaultValue', '')
			else:
				if setting == 'skills' or setting == 'supportedLanguages':
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

		# Setting logger level immediately
		if aliceConfigs['debug']:
			logging.getLogger('ProjectAlice').setLevel(logging.DEBUG)

		temp = aliceConfigs.copy()

		for k, v in temp.items():
			if k not in configTemplate.settings:
				self.logInfo(f'- Deprecated configuration: {k}')
				changes = True
				del aliceConfigs[k]

		if changes:
			self.writeToAliceConfigurationFile(aliceConfigs)

		return aliceConfigs


	def addSkillToAliceConfig(self, skillName: str, data: dict):
		self._skillsConfigurations[skillName] = data
		self.updateAliceConfiguration('skills', self._skillsConfigurations)
		self.loadCheckAndUpdateSkillConfigurations(skillName)


	def updateAliceConfiguration(self, key: str, value: typing.Any):
		if key not in self._aliceConfigurations:
			self.logWarning(f'Was asked to update {key} but key doesn\'t exist')
			raise ConfigurationUpdateFailed()

		try:
			# Remove skill configurations
			if key == 'skills':
				value = {k: v for k, v in value.items() if k not in self._aliceSkillConfigurationKeys}
		except AttributeError:
			raise ConfigurationUpdateFailed()

		self._aliceConfigurations[key] = value
		self.writeToAliceConfigurationFile(self.aliceConfigurations)


	def updateSkillConfigurationFile(self, skillName: str, key: str, value: typing.Any):
		if skillName not in self._skillsConfigurations:
			self.logWarning(f'Was asked to update {key} in skill {skillName} but skill doesn\'t exist')
			return

		if key not in self._skillsConfigurations[skillName]:
			self.logWarning(f'Was asked to update {key} in skill {skillName} but key doesn\'t exist')
			return

		# Cast value to template defined type
		vartype = self._skillsTemplateConfigurations[skillName][key]['dataType']
		if vartype == 'boolean':
			if value.lower() in {'on', 'yes', 'true', 'active'}:
				value = True
			elif value.lower() in {'off', 'no', 'false', 'inactive'}:
				value = False
		elif vartype == 'integer':
			try:
				value = int(value)
			except:
				self.logWarning(f'Value missmatch for config {key} in skill {skillName}')
				value = 0
		elif vartype == 'float':
			try:
				value = float(value)
			except:
				self.logWarning(f'Value missmatch for config {key} in skill {skillName}')
				value = 0.0
		elif vartype in {'string', 'email', 'password'}:
			try:
				value = str(value)
			except:
				self.logWarning(f'Value missmatch for config {key} in skill {skillName}')
				value = ''

		self._skillsConfigurations[skillName][key] = value
		self._writeToSkillConfigurationFile(skillName, self._skillsConfigurations[skillName])


	def writeToAliceConfigurationFile(self, confs: dict):
		"""
		Saves the given configuration into config.py
		:param confs: the dict to save
		"""
		sort = dict(sorted(confs.items()))

		# Only store "active", "version", "author", "conditions" value for skill config
		misterProper = ['active', 'version', 'author', 'conditions']

		# pop skills key so it gets added in the back
		skills = sort.pop('skills')
		skills = dict() if not isinstance(skills, dict) else skills

		sort['skills'] = dict()
		for skillName, setting in skills.items():
			skillCleaned = {key: value for key, value in setting.items() if key in misterProper}
			sort['skills'][skillName] = skillCleaned

		self._aliceConfigurations = sort

		try:
			confString = json.dumps(sort, indent=4).replace('false', 'False').replace('true', 'True')
			Path('config.py').write_text(f'settings = {confString}')
			importlib.reload(config)
		except Exception:
			raise ConfigurationUpdateFailed()


	def _writeToSkillConfigurationFile(self, skillName: str, confs: dict):
		"""
		Saves the given configuration into config.py of the Skill
		:param skillName: the targeted skill
		:param confs: the dict to save
		"""

		# Don't store "active", "version", "author", "conditions" value in skill config file
		misterProper = ['active', 'version', 'author', 'conditions']
		confsCleaned = {key: value for key, value in confs.items() if key not in misterProper}

		skillConfigFile = Path(self.Commons.rootDir(), 'skills', skillName, 'config.json')
		skillConfigFile.write_text(json.dumps(confsCleaned, indent=4))


	def loadSnipsConfigurations(self) -> TomlFile:
		self.logInfo('Loading Snips configuration file')

		snipsConfigPath = Path('/etc/snips.toml')
		snipsConfigTemplatePath = Path(self.Commons.rootDir(), 'system/snips/snips.toml')

		if not snipsConfigPath.exists():
			self.Commons.runRootSystemCommand(['cp', snipsConfigTemplatePath, '/etc/snips.toml'])
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
			conf = self._snipsConfigurations[parent][key]  # TomlFile does auto create missing keys
			self._snipsConfigurations.dump()
			return conf

		config = self._snipsConfigurations[parent].get(key, None)
		if config is None:
			self.logWarning(f'Tried to get "{parent}/{key}" in snips configuration but key was not found')

		return config


	def configAliceExists(self, configName: str) -> bool:
		return configName in self._aliceConfigurations


	def configSkillExists(self, configName: str, skillName: str) -> bool:
		return skillName in self._skillsConfigurations and configName in self._skillsConfigurations[skillName]


	def getAliceConfigByName(self, configName: str, voiceControl: bool = False) -> typing.Any:
		return self._aliceConfigurations.get(
			configName,
			difflib.get_close_matches(word=configName, possibilities=self._aliceConfigurations, n=3) if voiceControl else ''
		)


	def getSkillConfigByName(self, skillName: str, configName: str) -> typing.Any:
		return self._skillsConfigurations.get(skillName, dict()).get(configName, None)


	def getSkillConfigs(self, skillName: str) -> dict:
		return self._skillsConfigurations.get(skillName, dict())


	def getSkillConfigsTemplateByName(self, skillName: str, configName: str) -> typing.Any:
		return self._skillsTemplateConfigurations.get(skillName, dict()).get(configName, None)


	def getSkillConfigsTemplate(self, skillName: str) -> dict:
		return self._skillsTemplateConfigurations.get(skillName, dict())


	def loadCheckAndUpdateSkillConfigurations(self, skill: str = None):
		skillsConfigurations = dict()

		skillsPath = Path(self.Commons.rootDir() + '/skills')
		for skillDirectory in skillsPath.glob('*'):
			if not skillDirectory.is_dir() or (skill is not None and skillDirectory.stem != skill) or skillDirectory.stem.startswith('_'):
				continue

			self.logInfo(f'Checking configuration for skill {skillDirectory.stem}')

			skillConfigFile = Path(skillsPath / skillDirectory / 'config.json')
			skillConfigTemplate = Path(skillsPath / skillDirectory / 'config.json.template')
			skillName = skillDirectory.stem
			config = dict()

			if not skillConfigFile.exists() and skillConfigTemplate.exists():
				self._newSkillConfigFile(skillName, skillConfigTemplate)
				config = json.load(skillConfigFile.open())

			elif skillConfigFile.exists() and not skillConfigTemplate.exists():
				self.logInfo(f'- Deprecated config file for skill "{skillName}", removing')
				skillConfigFile.unlink()
				self._skillsTemplateConfigurations[skillName] = dict()
				skillsConfigurations[skillName] = dict()

			elif skillConfigFile.exists() and skillConfigTemplate.exists():
				config = json.load(skillConfigFile.open())
				configSample = json.load(skillConfigTemplate.open())
				self._skillsTemplateConfigurations[skillName] = configSample

				try:
					changes = False
					for setting, definition in configSample.items():
						if setting not in config:
							self.logInfo(f'- New configuration found for skill "{skillName}": {setting}')
							changes = True
							config[setting] = definition['defaultValue']

						elif 'defaultValue' in definition and not isinstance(config[setting], type(definition['defaultValue'])):
							changes = True
							try:
								# First try to cast the seting we have to the new type
								config[setting] = type(definition['defaultValue'])(config[setting])
								self.logInfo(f'- Existing configuration type missmatch for skill "{skillName}": {setting}, cast variable to template configuration type')
							except Exception:
								# If casting failed let's fall back to the new default value
								self.logInfo(f'- Existing configuration type missmatch for skill "{skillName}": {setting}, replaced with template configuration')
								config[setting] = definition['defaultValue']

					temp = config.copy()
					for k, v in temp.items():
						if k not in configSample:
							self.logInfo(f'- Deprecated configuration for skill "{skillName}": {k}')
							changes = True
							del config[k]

					if changes:
						self._writeToSkillConfigurationFile(skillName, config)
				except Exception as e:
					self.logWarning(f'- Failed updating existing skill config file for skill {skillName}: {e}')
					skillConfigFile.unlink()
					if skillConfigTemplate.exists():
						self._newSkillConfigFile(skillName, skillConfigTemplate)
					else:
						self.logWarning(f'- Cannot create config, template not existing, skipping skill "{skillName}"')

			else:
				self._skillsTemplateConfigurations[skillName] = dict()
				skillsConfigurations[skillName] = dict()

			if skillName in self._aliceConfigurations['skills']:
				config = {**config, **self._aliceConfigurations['skills'][skillName]}
			else:
				# For some reason we have a skill not declared in alice configs... I think getting rid of it is best
				if skillName not in SkillManager.NEEDED_SKILLS and not self.getAliceConfigByName('devMode'):
					self.logInfo(f'- Skill "{skillName}" not declared in config but files are existing, cleaning up')
					shutil.rmtree(skillDirectory, ignore_errors=True)
					if skillName in skillsConfigurations:
						skillsConfigurations.pop(skillName)
					continue
				elif skillName in SkillManager.NEEDED_SKILLS:
					self.logInfo(f'- Skill "{skillName}" is required but is missing definition in Alice config, generating them')
				elif self.getAliceConfigByName('devMode'):
					self.logInfo(f'- Dev mode is on, "{skillName}" is missing definition in Alice config, generating them')

				try:
					installFile = json.load(Path(skillsPath / skillDirectory / f'{skillName}.install').open())
					node = {
						'active': True,
						'version': installFile['version'],
						'author': installFile['author'],
						'conditions': installFile['conditions']
					}
					config = {**config, **node}
					self._skillsConfigurations[skillName] = config
					self.updateAliceConfiguration('skills', self._skillsConfigurations)
				except Exception as e:
					if self.getAliceConfigByName('devMode'):
						self.logInfo(f'- Failed generating default config. Please check your config template for skill "{skillName}"')
						continue
					else:
						self.logError(f'- Failed generating default config, scheduling download for skill "{skillName}": {e}')
						self.Commons.downloadFile(f'https://skills.projectalice.ch/{skillName}', f'system/skillInstallTickets/{skillName}.install')
						if skillName in skillsConfigurations:
							skillsConfigurations.pop(skillName)
						continue

			if config:
				skillsConfigurations[skillName] = config

		self._skillsConfigurations = {**self._skillsConfigurations, **skillsConfigurations}


	def _newSkillConfigFile(self, skillName: str, skillConfigTemplate: Path):
		self.logInfo(f'- New config file for skill "{skillName}", creating from template')

		template = json.load(skillConfigTemplate.open())

		confs = {configName: configData['defaultValue'] if 'defaultValue' in configData else configData for configName, configData in template.items()}
		self._skillsTemplateConfigurations[skillName] = template
		self._skillsConfigurations[skillName] = confs
		self._writeToSkillConfigurationFile(skillName, confs)


	def deactivateSkill(self, skillName: str, persistent: bool = False):

		if skillName in self.aliceConfigurations['skills']:
			self.logInfo(f"Deactivated skill {skillName} {'with' if persistent else 'without'} persistence")
			self.aliceConfigurations['skills'][skillName]['active'] = False

			if persistent:
				self.writeToAliceConfigurationFile(self._aliceConfigurations)


	def activateSkill(self, skillName: str, persistent: bool = False):

		if skillName in self.aliceConfigurations['skills']:
			self.logInfo(f"Activated skill {skillName} {'with' if persistent else 'without'} persistence")
			self.aliceConfigurations['skills'][skillName]['active'] = True

			if persistent:
				self.writeToAliceConfigurationFile(self._aliceConfigurations)


	def removeSkill(self, skillName: str):
		if skillName in self.aliceConfigurations['skills']:
			skills = self.aliceConfigurations['skills']
			del skills[skillName]
			self.aliceConfigurations['skills'] = skills
			self.writeToAliceConfigurationFile(self._aliceConfigurations)


	def changeActiveLanguage(self, toLang: str):
		if toLang in self.getAliceConfigByName('supportedLanguages'):
			self.updateAliceConfiguration('activeLanguage', toLang)
			return True
		return False


	def getAliceConfigType(self, confName: str) -> typing.Optional[str]:
		# noinspection PyTypeChecker
		return self._aliceConfigurations.get(confName['dataType'])


	def isAliceConfHidden(self, confName: str) -> bool:
		return confName in self._aliceTemplateConfigurations and \
		       self._aliceTemplateConfigurations.get('display') == 'hidden'


	def getAliceConfUpdatePostProcessing(self, confName: str) -> typing.Optional[str]:
		# Some config need some post processing if updated while Alice is running
		return self._aliceTemplateConfigurations.get(confName, dict()).get('onUpdate')


	def doConfigUpdatePostProcessing(self, functions: list):
		# Call alice config post processing functions. This will call methods that are needed after a certain setting was
		# updated while Project Alice was running
		for function in functions:
			try:
				func = getattr(self, function)
				func()
			except:
				self.logWarning(f'Configuration post processing method "{function}" does not exist')
				continue


	def reconnectMqtt(self):
		self.MqttManager.reconnect()


	def reloadASR(self):
		self.ASRManager.onStop()
		self.ASRManager.onStart()


	def refreshStoreData(self):
		self.SkillStoreManager.refreshStoreData()


	def getGithubAuth(self) -> tuple:
		username = self.getAliceConfigByName('githubUsername')
		token = self.getAliceConfigByName('githubToken')
		return (username, token) if (username and token) else None


	@property
	def snipsConfigurations(self) -> TomlFile:
		return self._snipsConfigurations


	@property
	def aliceConfigurations(self) -> dict:
		return self._aliceConfigurations


	@property
	def skillsConfigurations(self) -> dict:
		return self._skillsConfigurations


	@property
	def vitalConfigs(self) -> list:
		return self._vitalConfigs


	@property
	def aliceSkillConfigurationKeys(self) -> list:
		return self._aliceSkillConfigurationKeys


	@property
	def aliceTemplateConfigurations(self) -> dict:
		return self._aliceTemplateConfigurations
