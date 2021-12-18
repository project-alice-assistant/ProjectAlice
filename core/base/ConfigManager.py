#  Copyright (c) 2021
#
#  This file, ConfigManager.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:45 CEST
import inspect
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import sounddevice as sd

from core.ProjectAliceExceptions import ConfigurationUpdateFailed, VitalConfigMissing
from core.base.SuperManager import SuperManager
from core.base.model.Manager import Manager
from core.webui.model.UINotificationType import UINotificationType


class ConfigManager(Manager):
	TEMPLATE_FILE = Path('configTemplate.json')
	CONFIG_FILE = Path('config.json')

	CONFIG_FUNCTION_REGEX = re.compile(r'^(?:(?P<manager>\w+)\.)?(?P<function>\w+)(?:\((?P<args>.*)\))?')
	CONFIG_FUNCTION_ARG_REGEX = re.compile(r'(?:\w+)')


	def __init__(self):
		super().__init__()

		self.configFileExists = False
		self._loadingDone = False

		self._vitalConfigs = list()
		self._aliceConfigurationCategories = list()

		self._aliceTemplateConfigurations: Dict[str, dict] = self.loadJsonFromFile(self.TEMPLATE_FILE)
		self._aliceConfigurations: Dict[str, Any] = dict()

		self._loadCheckAndUpdateAliceConfigFile()

		self._skillsConfigurations = dict()
		self._skillsTemplateConfigurations: Dict[str, dict] = dict()

		self._pendingAliceConfUpdates = dict()


	def onStart(self):
		super().onStart()

		for conf in self._vitalConfigs:
			if conf not in self._aliceConfigurations or self._aliceConfigurations[conf] == '':
				raise VitalConfigMissing(conf)

		for setting, definition in {**self._aliceTemplateConfigurations, **self._skillsTemplateConfigurations}.items():
			function = definition.get('onStart', None)
			if function:
				try:
					if '.' in function:
						self.logWarning(f'Use of manager for configuration **onStart** for config "{setting}" is not allowed')
						function = function.split('.')[-1]

					func = getattr(self, function)
					func()
				except AttributeError:
					self.logWarning(f'Configuration onStart method **{function}** does not exist')
				except Exception as e:
					self.logError(f'Configuration onStart method **{function}** failed: {e}')


	def _loadCheckAndUpdateAliceConfigFile(self):
		self.logInfo('Checking Alice configuration file')

		try:
			aliceConfigs = self.loadJsonFromFile(self.CONFIG_FILE)
		except Exception:
			self.logWarning(f'No {str(self.CONFIG_FILE)} found.')
			aliceConfigs = dict()

		if not aliceConfigs:
			self.logInfo('Creating config file from config template')
			aliceConfigs = {configName: configData['defaultValue'] if 'defaultValue' in configData else configData for configName, configData in self._aliceTemplateConfigurations.items()}
			self.CONFIG_FILE.write_text(json.dumps(aliceConfigs, indent='\t', ensure_ascii=False))

		changes = False

		# most important: uuid is always required!
		if not aliceConfigs.get('uuid', None):
			import uuid

			##uuid4: no collision expected until extinction of all life (only on earth though!)
			aliceConfigs['uuid'] = str(uuid.uuid4())
			changes = True

		for setting, definition in self._aliceTemplateConfigurations.items():

			if definition['category'] not in self._aliceConfigurationCategories:
				self._aliceConfigurationCategories.append(definition['category'])

			if setting not in aliceConfigs:
				self.logInfo(f'New configuration found: **{setting}**')
				changes = True
				aliceConfigs[setting] = definition.get('defaultValue', '')
			else:
				if setting == 'supportedLanguages':
					continue

				if definition['dataType'] != 'list' and definition['dataType'] != 'longstring' and 'onInit' not in definition:
					if not isinstance(aliceConfigs[setting], type(definition['defaultValue'])):
						changes = True
						try:
							# First try to cast the setting we have to the new type
							aliceConfigs[setting] = type(definition['defaultValue'])(aliceConfigs[setting])
							self.logWarning(f'Existing configuration type mismatch: **{setting}**, cast variable to template configuration type')
						except Exception:
							# If casting failed let's fall back to the new default value
							self.logWarning(f'Existing configuration type mismatch: **{setting}**, replaced with template configuration')
							aliceConfigs[setting] = definition['defaultValue']
				elif definition['dataType'] == 'list' and 'onInit' not in definition:
					values = definition['values'].values() if isinstance(definition['values'], dict) else definition['values']

					if aliceConfigs[setting] and aliceConfigs[setting] not in values:
						changes = True
						self.logWarning(f"Selected value **{aliceConfigs[setting]}** for setting **{setting}** doesn't exist, reverted to default value --{definition['defaultValue']}--")
						aliceConfigs[setting] = definition['defaultValue']

				function = definition.get('onInit', None)
				if function:
					try:
						if '.' in function:
							self.logWarning(f'Use of manager for configuration **onInit** for config "{setting}" is not allowed')
							function = function.split('.')[-1]

						func = getattr(self, function)
						func()
					except AttributeError:
						self.logWarning(f'Configuration onInit method **{function}** does not exist')
					except Exception as e:
						self.logError(f'Configuration onInit method **{function}** failed: {e}')

		# Setting logger level immediately
		if aliceConfigs['advancedDebug'] and not aliceConfigs['debug']:
			aliceConfigs['debug'] = True
			changes = True

		if aliceConfigs['debug']:
			logging.getLogger('ProjectAlice').setLevel(logging.DEBUG)

		# Load asound if needed
		if not aliceConfigs['asoundConfig']:
			asound = Path('/etc/asound.conf')
			if asound.exists():
				changes = True
				aliceConfigs['asoundConfig'] = asound.read_text()

		temp = aliceConfigs.copy()
		for key in temp:
			if key not in self._aliceTemplateConfigurations:
				self.logInfo(f'Deprecated configuration: **{key}**')
				changes = True
				del aliceConfigs[key]

		if changes:
			self.writeToAliceConfigurationFile(aliceConfigs)
		else:
			self._aliceConfigurations = aliceConfigs


	def updateAliceConfigDefinitionValues(self, setting: str, value: Any):
		if setting not in self._aliceTemplateConfigurations:
			self.logWarning(f"Was asked to update **{setting}** from config templates, but setting doesn't exist")
			return

		self._aliceTemplateConfigurations[setting]['values'] = value


	@staticmethod
	def loadJsonFromFile(jsonFile: Path) -> dict:
		try:
			return json.loads(jsonFile.read_text())
		except:
			# Prevents failing for caller
			raise


	def updateMainDeviceName(self, value: Any):
		device = self.DeviceManager.getMainDevice()

		if not device.displayName:
			device.updateConfigs(configs={'displayName': 'Alice'})
		if value != device.displayName:
			device.updateConfigs(configs={'displayName': value})


	def updateAliceConfiguration(self, key: str, value: Any, dump: bool = True, doPreAndPostProcessing: bool = True):
		"""
		Updating a core config is sensitive, if the request comes from a skill.
		First check if the request came from a skill at anytime and if so ask permission
		to the user
		:param doPreAndPostProcessing: If set to false, all pre and post processing won't be called
		:param key: str
		:param value: str
		:param dump: bool If set to False, the configs won't be dumped to the json file
		:return: None
		"""

		rootSkills = [name.lower() for name in self.SkillManager.NEEDED_SKILLS]
		callers = [inspect.getmodulename(frame[1]).lower() for frame in inspect.stack()]
		if 'aliceskill' in callers:
			skillName = callers[callers.index('aliceskill') + 1]
			if skillName not in rootSkills:
				self._pendingAliceConfUpdates[key] = value
				self.logWarning(f'Skill **{skillName}** is trying to modify a core configuration')

				self.WebUINotificationManager.newNotification(typ=UINotificationType.ALERT, notification='coreConfigUpdateWarning', replaceBody=[skillName, key, value])
				return

		if key not in self._aliceConfigurations:
			self.logWarning(f"Was asked to update **{key}** but key doesn't exist")
			raise ConfigurationUpdateFailed()

		pre = self.getAliceConfUpdatePreProcessing(key)
		if doPreAndPostProcessing and pre and not self.ConfigManager.doConfigUpdatePreProcessing(pre, value):
			return

		if key == 'deviceName':
			self.updateMainDeviceName(value=value)

		self._aliceConfigurations[key] = value

		if dump:
			self.writeToAliceConfigurationFile()

		pp = self.ConfigManager.getAliceConfUpdatePostProcessing(key)
		if doPreAndPostProcessing and pp:
			self.ConfigManager.doConfigUpdatePostProcessing(pp)


	def bulkUpdateAliceConfigurations(self):
		if not self._pendingAliceConfUpdates:
			return

		for key, value in self._pendingAliceConfUpdates.items():
			if key not in self._aliceConfigurations:
				self.logWarning(f"Was asked to update **{key}** but key doesn't exist")
				continue
			self.updateAliceConfiguration(key, value, False)

		self.writeToAliceConfigurationFile()
		self.deletePendingAliceConfigurationUpdates()


	def deletePendingAliceConfigurationUpdates(self):
		self._pendingAliceConfUpdates = dict()


	def updateSkillConfigurationFile(self, skillName: str, key: str, value: Any):
		if skillName not in self._skillsConfigurations:
			self.logWarning(f"Was asked to update **{key}** in skill **{skillName}** but skill doesn't exist")
			return

		if key not in self._skillsConfigurations[skillName]:
			self.logWarning(f"Was asked to update **{key}** in skill **{skillName}** but key doesn't exist")
			return

		# Cast value to template defined type
		vartype = self._skillsTemplateConfigurations[skillName][key]['dataType']
		if vartype == 'boolean':
			if not isinstance(value, bool):
				if value.lower() in {'on', 'yes', 'true', 'active'}:
					value = True
				elif value.lower() in {'off', 'no', 'false', 'inactive'}:
					value = False
		elif vartype == 'integer':
			try:
				value = int(value)
			except:
				self.logWarning(f'Value mismatch for config **{key}** in skill **{skillName}**')
				value = 0
		elif vartype == 'float' or vartype == 'range':
			try:
				value = float(value)
				if vartype == 'range' and (value > self._skillsTemplateConfigurations[skillName][key]['max'] or value < self._skillsTemplateConfigurations[skillName][key]['min']):
					value = self._skillsTemplateConfigurations[skillName][key]['defaultValue']
					self.logWarning(f'Value for config **{key}** in skill **{skillName}** is out of bound, reverted to default')
			except:
				self.logWarning(f'Value mismatch for config **{key}** in skill **{skillName}**')
				value = 0
		elif vartype in {'string', 'email', 'password', 'longstring'}:
			try:
				value = str(value)
			except:
				self.logWarning(f'Value mismatch for config **{key}** in skill **{skillName}**')
				value = ''

		if self._skillsConfigurations[skillName][key] == value:
			return  # don't call any before/onUpdate if nothing changed

		skillInstance = self.SkillManager.getSkillInstance(skillName=skillName, silent=True)
		if self._skillsTemplateConfigurations[skillName][key].get('beforeUpdate', None):
			if not skillInstance:
				self.logWarning(f'Needed to execute an action before updating a config value for skill **{skillName}** but the skill is not running')
			else:
				function = self._skillsTemplateConfigurations[skillName][key]['beforeUpdate']
				try:
					func = getattr(skillInstance, function)
				except AttributeError:
					self.logWarning(f'Configuration pre processing method **{function}** for skill **{skillName}** does not exist')
				else:
					try:
						if not func(value):
							self.logWarning(f'Configuration pre processing method **{function}** for skill **{skillName}** returned False, cancel setting update')
							return
					except Exception as e:
						self.logError(f'Configuration pre processing method **{function}** for skill **{skillName}** failed: {e}')

		self._skillsConfigurations[skillName][key] = value
		self._writeToSkillConfigurationFile(skillName, self._skillsConfigurations[skillName])

		if self._skillsTemplateConfigurations[skillName][key].get('onUpdate', None):
			if not skillInstance:
				self.logWarning(f'Needed to execute an action after updating a config value for skill **{skillName}** but the skill is not running')
			else:
				function = self._skillsTemplateConfigurations[skillName][key]['onUpdate']
				try:
					func = getattr(skillInstance, function)
				except AttributeError:
					self.logWarning(f'Configuration post processing method **{function}** for skill **{skillName}** does not exist')
				else:
					try:
						if not func(value):
							self.logWarning(f'Configuration post processing method **{function}** for skill **{skillName}** returned False')
					except Exception as e:
						self.logError(f'Configuration post processing method **{function}** for skill **{skillName}** failed: {e}')


	def writeToAliceConfigurationFile(self, confs: dict = None):
		"""
		Saves the given configuration into config.json
		:param confs: the dict to save
		"""
		confs = confs if confs else self._aliceConfigurations

		# noinspection PyTypeChecker
		sort = dict(sorted(confs.items()))
		self._aliceConfigurations = sort

		try:
			self.CONFIG_FILE.write_text(json.dumps(sort, indent='\t', sort_keys=True))
		except Exception:
			raise ConfigurationUpdateFailed()


	def _writeToSkillConfigurationFile(self, skillName: str, confs: dict):
		"""
		Saves the given configuration into config.json of the Skill
		:param skillName: the targeted skill
		:param confs: the dict to save
		"""

		# Don't store "active", "version", "author", "conditions" value in skill config file
		misterProper = ['active', 'version', 'author', 'conditions']
		confsCleaned = {key: value for key, value in confs.items() if key not in misterProper}

		skillConfigFile = Path(self.Commons.rootDir(), 'skills', skillName, 'config.json')
		skillConfigFile.write_text(json.dumps(confsCleaned, indent='\t', ensure_ascii=False, sort_keys=True))


	def configAliceExists(self, configName: str) -> bool:
		return configName in self._aliceConfigurations


	def configSkillExists(self, configName: str, skillName: str) -> bool:
		return skillName in self._skillsConfigurations and configName in self._skillsConfigurations[skillName]


	def getAliceConfigByName(self, configName: str) -> Any:
		if configName in self._aliceConfigurations:
			return self._aliceConfigurations[configName]
		else:
			self.logDebug(f'Trying to get config **{configName}** but it does not exist')
			return ''


	def getAliceConfigTemplateByName(self, configName: str) -> Any:
		if configName in self._aliceTemplateConfigurations:
			return self._aliceTemplateConfigurations[configName]
		else:
			self.logDebug(f'Trying to get config template **{configName}** but it does not exist')
			return ''


	def getSkillConfigByName(self, skillName: str, configName: str) -> Any:
		if not self._loadingDone:
			raise Exception(f'Loading skill configs is not yet done! Don\'t load configs in __init__, but only after onStart is called')
		return self._skillsConfigurations.get(skillName, dict()).get(configName, None)


	def getSkillConfigs(self, skillName: str) -> dict:
		return self._skillsConfigurations.get(skillName, dict())


	def getSkillConfigsTemplateByName(self, skillName: str, configName: str) -> Any:
		return self._skillsTemplateConfigurations.get(skillName, dict()).get(configName, None)


	def getSkillConfigsTemplate(self, skillName: str) -> dict:
		return self._skillsTemplateConfigurations.get(skillName, dict())


	def loadCheckAndUpdateSkillConfigurations(self, skillToLoad: str = None):
		skillsConfigurations = dict()

		for skillName, skillInstance in self.SkillManager.activeSkills.items():

			if skillToLoad and skillName != skillToLoad:
				continue

			self.logInfo(f'Checking configuration for skill **{skillName}**')

			skillConfigFile = skillInstance.getResource(str(self.CONFIG_FILE))
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
								self.logInfo(f'- Existing configuration type mismatch for skill **{skillName}**: {setting}, cast variable to template configuration type')
							except Exception:
								# If casting failed let's fall back to the new default value
								self.logInfo(f'- Existing configuration type mismatch for skill **{skillName}**: {setting}, replaced with template configuration')
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

		if not skillToLoad:
			self._skillsConfigurations = skillsConfigurations.copy()
		else:
			self._skillsConfigurations[skillToLoad] = skillsConfigurations[skillToLoad].copy()
		self._loadingDone = True


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


	def getAliceConfigType(self, confName: str) -> Optional[str]:
		# noinspection PyTypeChecker
		return self._aliceConfigurations.get(confName['dataType'])


	def isAliceConfHidden(self, confName: str) -> bool:
		return self._aliceTemplateConfigurations.get(confName, dict()).get('display', '') == 'hidden'


	def isAliceConfSensitive(self, confName: str) -> bool:
		return self._aliceTemplateConfigurations.get(confName, dict()).get('isSensitive', False)


	def getAliceConfUpdatePreProcessing(self, confName: str) -> Optional[str]:
		# Some config need some pre processing to run some checks before saving
		return self._aliceTemplateConfigurations.get(confName, dict()).get('beforeUpdate', None)


	def getAliceConfUpdatePostProcessing(self, confName: str) -> Optional[str]:
		# Some config need some post processing if updated while Alice is running
		return self._aliceTemplateConfigurations.get(confName, dict()).get('onUpdate', None)


	def doConfigUpdatePreProcessing(self, function: str, value: Any) -> bool:
		# Call alice config pre processing functions.
		try:
			mngr = self
			args = list()

			result = self.CONFIG_FUNCTION_REGEX.search(function)
			if result:
				function = result.group('function')

				if result.group('manager'):
					try:
						mngr = getattr(self, result.group('manager'))
					except AttributeError:
						self.logWarning(f'Config pre processing manager **{result.group("manager")}** does not exist')
						return False

				if result.group('args'):
					args = self.CONFIG_FUNCTION_ARG_REGEX.findall(result.group('args'))

				func = getattr(mngr, function)
			else:
				raise AttributeError
		except AttributeError:
			self.logWarning(f'Configuration pre processing method **{function}** does not exist')
			return False
		else:
			try:
				return func(value, *args)
			except Exception as e:
				self.logError(f'Configuration pre processing method **{function}** failed: {e}')
				return False


	def doConfigUpdatePostProcessing(self, functions: Union[str, set]):
		# Call alice config post processing functions. This will call methods that are needed after a certain setting was
		# updated while Project Alice was running

		if isinstance(functions, str):
			functions = {functions}

		for function in functions:
			try:
				mngr = self
				args = list()

				result = self.CONFIG_FUNCTION_REGEX.search(function)
				if result:
					function = result.group('function')

					if result.group('manager'):
						try:
							mngr = getattr(self, result.group('manager'))
						except AttributeError:
							self.logWarning(f'Config post processing manager **{result.group("manager")}** does not exist')
							return False

					if result.group('args'):
						args = self.CONFIG_FUNCTION_ARG_REGEX.findall(result.group('args'))

					func = getattr(mngr, function)
				else:
					raise AttributeError
			except AttributeError:
				self.logWarning(f'Configuration post processing method **{function}** does not exist')
				continue
			else:
				try:
					func(*args)
				except Exception as e:
					self.logError(f'Configuration post processing method **{function}** failed: {e}')
					continue


	def updateMqttSettings(self):
		self.NluManager.restartEngine()
		if self.getAliceConfigByName('wakewordEngine') == 'snips':
			self.WakewordManager.restartEngine()
		if self.getAliceConfigByName('asr') == 'snips' or self.getAliceConfigByName('asrFallback') == 'snips':
			self.ASRManager.restartEngine()

		self.reconnectMqtt()


	def reconnectMqtt(self):
		self.MqttManager.reconnect()


	def reloadASRManager(self):
		SuperManager.getInstance().restartManager(manager=self.ASRManager.name)


	def reloadTTSManager(self):
		SuperManager.getInstance().restartManager(manager=self.TTSManager.name)


	def reloadNLUManager(self):
		SuperManager.getInstance().restartManager(manager=self.NluManager.name)


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
		if self.getAliceConfigByName('disableSound'):
			self.AudioServer.onStop()
		else:
			self.AudioServer.onStart()


	def enableDisableCapture(self):
		if self.getAliceConfigByName('disableCapture'):
			self.WakewordManager.disableEngine()
		else:
			self.WakewordManager.enableEngine()


	def reloadWakeword(self):
		SuperManager.getInstance().restartManager(manager=self.WakewordManager.name)


	def refreshStoreData(self):
		self.SkillStoreManager.refreshStoreData()


	def injectAsound(self, newSettings: str):
		newSettings = newSettings.replace('\r\n', '\n')
		if self.getAliceConfigByName('asoundConfig') and self.getAliceConfigByName('asoundConfig') != newSettings:
			tmp = Path('/tmp/asound')
			tmp.write_text(newSettings)
			self.Commons.runRootSystemCommand(['sudo', 'mv', tmp, '/etc/asound.conf'])
			self.Commons.runRootSystemCommand(['sudo', 'alsactl', 'kill', 'rescan'])
			self.logInfo("Wrote new asound.conf")
			return True


	def updateTimezone(self, newTimezone: str):
		result = self.Commons.runRootSystemCommand(['timedatectl', 'set-timezone', newTimezone])
		if result.returncode:
			self.logError('Unsupported timezone format')


	def toggleDebugLogs(self):
		if self.getAliceConfigByName('debug'):
			logging.getLogger('ProjectAlice').setLevel(logging.DEBUG)
		else:
			logging.getLogger('ProjectAlice').setLevel(logging.WARN)


	def populateAudioInputConfig(self):
		try:
			devices = self._listAudioDevices()
			self.updateAliceConfigDefinitionValues(setting='inputDevice', value=devices)
		except:
			if not self.getAliceConfigByName('disableCapture'):
				self.logWarning('No audio input device found')


	def populateAudioOutputConfig(self):
		try:
			devices = self._listAudioDevices()
			self.updateAliceConfigDefinitionValues(setting='outputDevice', value=devices)
		except:
			if not self.getAliceConfigByName('disableSound'):
				self.logWarning('No audio output device found')


	@staticmethod
	def _listAudioDevices() -> List:
		try:
			devices = [device['name'] for device in sd.query_devices()]
			if not devices:
				raise Exception
		except:
			raise

		return devices


	@property
	def aliceConfigurations(self) -> Dict:
		return self._aliceConfigurations


	@property
	def aliceConfigurationCategories(self) -> List:
		return sorted(self._aliceConfigurationCategories)


	@property
	def vitalConfigs(self) -> List:
		return self._vitalConfigs


	@property
	def aliceTemplateConfigurations(self) -> Dict:
		return self._aliceTemplateConfigurations


	@property
	def githubAuth(self) -> Tuple[str, str]:
		"""
		Returns the users configured username and token for Github as a tuple
		When one of the values is not supplied None is returned.
		:return:
		"""
		username = self.getAliceConfigByName('githubUsername')
		token = self.getAliceConfigByName('githubToken')
		return (username, token) if (username and token) else None
