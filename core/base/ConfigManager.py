import json
import logging
from pathlib import Path

import configTemplate
from core.base.SuperManager import SuperManager
from core.base.model.TomlFile import TomlFile

try:
	# noinspection PyUnresolvedReferences,PyPackageRequirements
	import config

	configFileExist = True
except ModuleNotFoundError:
	configFileNotExist = False

import importlib
import typing
from core.ProjectAliceExceptions import ConfigurationUpdateFailed, VitalConfigMissing
from core.base.model.Manager import Manager


class ConfigManager(Manager):

	CONFIG_FILE = 'config.py'

	def __init__(self):
		super().__init__()

		self._vitalConfigs = list()
		self._aliceConfigurationCategories = list()

		self._aliceConfigurations: typing.Dict[str, typing.Any] = self._loadCheckAndUpdateAliceConfigFile()
		self._aliceTemplateConfigurations: typing.Dict[str, dict] = configTemplate.settings

		self._snipsConfigurations = self.loadSnipsConfigurations()

		self._skillsConfigurations = dict()
		self._skillsTemplateConfigurations: typing.Dict[str, dict] = dict()


	def onStart(self):
		super().onStart()
		for conf in self._vitalConfigs:
			if conf not in self._aliceConfigurations or self._aliceConfigurations[conf] == '':
				raise VitalConfigMissing(conf)


	def _loadCheckAndUpdateAliceConfigFile(self) -> dict:
		self.logInfo('Checking Alice configuration file')

		if not configFileExist:
			self.logInfo('Creating config file from config template')
			confs = {configName: configData['defaultValue'] if 'defaultValue' in configData else configData for configName, configData in configTemplate.settings.items()}
			Path(self.CONFIG_FILE).write_text(f'settings = {json.dumps(confs, indent=4)}')
			aliceConfigs = importlib.import_module(self.CONFIG_FILE).settings.copy()
		else:
			aliceConfigs = config.settings.copy()

		changes = False
		for setting, definition in configTemplate.settings.items():

			if definition['category'] not in self._aliceConfigurationCategories:
				self._aliceConfigurationCategories.append(definition['category'])

			if setting not in aliceConfigs:
				self.logInfo(f'New configuration found: **{setting}**')
				changes = True
				aliceConfigs[setting] = definition.get('defaultValue', '')
			else:
				if setting == 'supportedLanguages':
					continue

				if definition['dataType'] != 'list' and definition['dataType'] != 'longstring':
					if not isinstance(aliceConfigs[setting], type(definition['defaultValue'])):
						changes = True
						try:
							# First try to cast the setting we have to the new type
							aliceConfigs[setting] = type(definition['defaultValue'])(aliceConfigs[setting])
							self.logWarning(f'Existing configuration type missmatch: **{setting}**, cast variable to template configuration type')
						except Exception:
							# If casting failed let's fall back to the new default value
							self.logWarning(f'Existing configuration type missmatch: **{setting}**, replaced with template configuration')
							aliceConfigs[setting] = definition['defaultValue']
				elif definition['dataType'] == 'list':
					values = definition['values'].values() if isinstance(definition['values'], dict) else definition['values']

					if aliceConfigs[setting] not in values:
						changes = True
						self.logWarning(f'Selected value **{aliceConfigs[setting]}** for setting **{setting}** doesn\'t exist, reverted to default value --{definition["defaultValue"]}--')
						aliceConfigs[setting] = definition['defaultValue']

		# Setting logger level immediately
		if aliceConfigs['debug']:
			logging.getLogger('ProjectAlice').setLevel(logging.DEBUG)

		temp = aliceConfigs.copy()
		for key in temp:
			if key not in configTemplate.settings:
				self.logInfo(f'Deprecated configuration: **{key}**')
				changes = True
				del aliceConfigs[key]

		if changes:
			self.writeToAliceConfigurationFile(aliceConfigs)

		return aliceConfigs


	def updateAliceConfiguration(self, key: str, value: typing.Any):
		if key not in self._aliceConfigurations:
			self.logWarning(f'Was asked to update **{key}** but key doesn\'t exist')
			raise ConfigurationUpdateFailed()

		self._aliceConfigurations[key] = value
		self.writeToAliceConfigurationFile(self.aliceConfigurations)


	def updateSkillConfigurationFile(self, skillName: str, key: str, value: typing.Any):
		if skillName not in self._skillsConfigurations:
			self.logWarning(f'Was asked to update **{key}** in skill **{skillName}** but skill doesn\'t exist')
			return

		if key not in self._skillsConfigurations[skillName]:
			self.logWarning(f'Was asked to update **{key}** in skill **{skillName}** but key doesn\'t exist')
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
				self.logWarning(f'Value missmatch for config **{key}** in skill **{skillName}**')
				value = 0
		elif vartype == 'float' or vartype == 'range':
			try:
				value = float(value)
				if vartype == 'range' and (value > self._skillsTemplateConfigurations[skillName][key]['max'] or value < self._skillsTemplateConfigurations[skillName][key]['min']):
					value = self._skillsTemplateConfigurations[skillName][key]['defaultValue']
					self.logWarning(f'Value for config **{key}** in skill **{skillName}** is out of bound, reverted to default')
			except:
				self.logWarning(f'Value missmatch for config **{key}** in skill **{skillName}**')
				value = 0
		elif vartype in {'string', 'email', 'password', 'longstring'}:
			try:
				value = str(value)
			except:
				self.logWarning(f'Value missmatch for config **{key}** in skill **{skillName}**')
				value = ''

		self._skillsConfigurations[skillName][key] = value
		self._writeToSkillConfigurationFile(skillName, self._skillsConfigurations[skillName])


	def writeToAliceConfigurationFile(self, confs: dict):
		"""
		Saves the given configuration into config.py
		:param confs: the dict to save
		"""
		sort = dict(sorted(confs.items()))
		self._aliceConfigurations = sort

		try:
			confString = json.dumps(sort, indent=4).replace('false', 'False').replace('true', 'True')
			Path(self.CONFIG_FILE).write_text(f'settings = {confString}')
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
				self.Commons.runRootSystemCommand(['systemctl', 'restart', 'snips-nlu'])


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
			self.logWarning(f'Tried to get **{parent}/{key}** in snips configuration but key was not found')
			return config

		return config


	def configAliceExists(self, configName: str) -> bool:
		return configName in self._aliceConfigurations


	def configSkillExists(self, configName: str, skillName: str) -> bool:
		return skillName in self._skillsConfigurations and configName in self._skillsConfigurations[skillName]


	def getAliceConfigByName(self, configName: str) -> typing.Any:
		if configName in self._aliceConfigurations:
			return self._aliceConfigurations[configName]
		else:
			self.logDebug(f'Trying to get config **{configName}** but it does not exist')
			return ''


	def getSkillConfigByName(self, skillName: str, configName: str) -> typing.Any:
		return self._skillsConfigurations.get(skillName, dict()).get(configName, None)


	def getSkillConfigs(self, skillName: str) -> dict:
		return self._skillsConfigurations.get(skillName, dict())


	def getSkillConfigsTemplateByName(self, skillName: str, configName: str) -> typing.Any:
		return self._skillsTemplateConfigurations.get(skillName, dict()).get(configName, None)


	def getSkillConfigsTemplate(self, skillName: str) -> dict:
		return self._skillsTemplateConfigurations.get(skillName, dict())


	def loadCheckAndUpdateSkillConfigurations(self, skillToLoad: str = None):
		skillsConfigurations = dict()

		for skillName, skillInstance in self.SkillManager.activeSkills.items():

			if skillToLoad and skillName != skillToLoad:
				continue

			self.logInfo(f'Checking configuration for skill **{skillName}**')

			skillConfigFile = skillInstance.getResource('config.json')
			skillConfigTemplate = skillInstance.getResource('config.json.template')
			config = dict()

			if not skillConfigFile.exists() and skillConfigTemplate.exists():
				self._newSkillConfigFile(skillName, skillConfigTemplate)
				config = json.load(skillConfigFile.open())

			elif skillConfigFile.exists() and not skillConfigTemplate.exists():
				self.logInfo(f'- Deprecated config file for skill **{skillName}**, removing')
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
							self.logInfo(f'- New configuration found for skill **{skillName}**: {setting}')
							changes = True
							config[setting] = definition['defaultValue']

						elif 'defaultValue' in definition and not isinstance(config[setting], type(definition['defaultValue'])):
							changes = True
							try:
								# First try to cast the setting we have to the new type
								config[setting] = type(definition['defaultValue'])(config[setting])
								self.logInfo(f'- Existing configuration type missmatch for skill **{skillName}**: {setting}, cast variable to template configuration type')
							except Exception:
								# If casting failed let's fall back to the new default value
								self.logInfo(f'- Existing configuration type missmatch for skill **{skillName}**: {setting}, replaced with template configuration')
								config[setting] = definition['defaultValue']

					temp = config.copy()
					for k, v in temp.items():
						if k not in configSample:
							self.logInfo(f'- Deprecated configuration for skill **{skillName}**: {k}')
							changes = True
							del config[k]

					if changes:
						self._writeToSkillConfigurationFile(skillName, config)
				except Exception as e:
					self.logWarning(f'- Failed updating existing skill config file for skill **{skillName}**: {e}')
					skillConfigFile.unlink()
					if skillConfigTemplate.exists():
						self._newSkillConfigFile(skillName, skillConfigTemplate)
					else:
						self.logWarning(f'- Cannot create config, template not existing, skipping skill **{skillName}**')

			else:
				self._skillsTemplateConfigurations[skillName] = dict()
				skillsConfigurations[skillName] = dict()

			if config:
				skillsConfigurations[skillName] = config

		self._skillsConfigurations = {**self._skillsConfigurations, **skillsConfigurations}


	def _newSkillConfigFile(self, skillName: str, skillConfigTemplate: Path):
		self.logInfo(f'- New config file for skill **{skillName}**, creating from template')

		template = json.load(skillConfigTemplate.open())

		confs = {configName: configData['defaultValue'] if 'defaultValue' in configData else configData for configName, configData in template.items()}
		self._skillsTemplateConfigurations[skillName] = template
		self._skillsConfigurations[skillName] = confs
		self._writeToSkillConfigurationFile(skillName, confs)


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


	def getAliceConfUpdatePreProcessing(self, confName: str) -> typing.Optional[str]:
		# Some config need some pre processing to run some checks before saving
		return self._aliceTemplateConfigurations.get(confName, dict()).get('beforeUpdate')


	def getAliceConfUpdatePostProcessing(self, confName: str) -> typing.Optional[str]:
		# Some config need some post processing if updated while Alice is running
		return self._aliceTemplateConfigurations.get(confName, dict()).get('onUpdate')


	def doConfigUpdatePreProcessing(self, function: str, value: typing.Any) -> bool:
		# Call alice config pre processing functions.
		try:
			func = getattr(self, function)
		except AttributeError:
			self.logWarning(f'Configuration pre processing method **{function}** does not exist')
			return False
		else:
			try:
				return func(value)
			except Exception as e:
				self.logError(f'Configuration pre processing method **{function}** failed: {e}')
				return False


	def doConfigUpdatePostProcessing(self, functions: set):
		# Call alice config post processing functions. This will call methods that are needed after a certain setting was
		# updated while Project Alice was running
		for function in functions:
			try:
				func = getattr(self, function)
			except AttributeError:
				self.logWarning(f'Configuration post processing method **{function}** does not exist')
				continue
			else:
				try:
					func()
				except Exception as e:
					self.logError(f'Configuration post processing method **{function}** failed: {e}')
					continue


	def updateMqttSettings(self):
		self.ConfigManager.updateSnipsConfiguration('snips-common', 'mqtt', f'{self.getAliceConfigByName("mqttHost")}:{self.getAliceConfigByName("mqttPort"):}', False, False)
		self.ConfigManager.updateSnipsConfiguration('snips-common', 'mqtt_username', self.getAliceConfigByName('mqttHost'), False, False)
		self.ConfigManager.updateSnipsConfiguration('snips-common', 'mqtt_password', self.getAliceConfigByName('mqttHost'), False, False)
		self.ConfigManager.updateSnipsConfiguration('snips-common', 'mqtt_tls_cafile', self.getAliceConfigByName('mqttHost'), True, False)
		self.reconnectMqtt()


	def reconnectMqtt(self):
		self.MqttManager.reconnect()


	def reloadASR(self):
		self.ASRManager.onStop()
		self.ASRManager.onStart()


	def reloadTTS(self):
		self.TTSManager.onStop()
		self.TTSManager.onStart()


	def checkNewAdminPinCode(self, pinCode: str) -> bool:
		try:
			pin = int(pinCode)
			if len(str(pin)) != 4:
				raise Exception

			return True
		except:
			self.logWarning('Pin code must be 4 digits')
			return False


	def updateAdminPinCode(self):
		self.UserManager.addUserPinCode('admin', self.getAliceConfigByName('adminPinCode'))


	def enableDisableSound(self):
		if self.getAliceConfigByName('disableSoundAndMic'):
			self.WakewordManager.disableEngine()
			self.AudioServer.onStop()
		else:
			self.WakewordManager.enableEngine()
			self.AudioServer.onStart()


	def restartWakewordEngine(self):
		self.WakewordManager.restartEngine()


	def reloadWakeword(self):
		SuperManager.getInstance().restartManager(manager=self.WakewordManager.name)


	def refreshStoreData(self):
		self.SkillStoreManager.refreshStoreData()


	def injectAsound(self, newSettings: str):
		newSettings = newSettings.replace('\r\n', '\n')
		if self.getAliceConfigByName('asoundConfig') != newSettings:
			tmp = Path('/tmp/asound')
			tmp.write_text(newSettings)
			self.Commons.runRootSystemCommand(['sudo', 'mv', tmp, '/etc/asound.conf'])
			self.Commons.runRootSystemCommand(['sudo', 'alsactl', 'kill', 'rescan'])


	def updateTimezone(self, newTimezone: str):
		result = self.Commons.runRootSystemCommand(['timedatectl', 'set-timezone', newTimezone])
		if result.returncode:
			self.logError('Unsupported timezone format')


	def toggleDebugLogs(self):
		if self.getAliceConfigByName('debug'):
			logging.getLogger('ProjectAlice').setLevel(logging.DEBUG)
		else:
			logging.getLogger('ProjectAlice').setLevel(logging.WARN)


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
	def aliceConfigurationCategories(self) -> list:
		return sorted(self._aliceConfigurationCategories)


	@property
	def vitalConfigs(self) -> list:
		return self._vitalConfigs


	@property
	def aliceTemplateConfigurations(self) -> dict:
		return self._aliceTemplateConfigurations
