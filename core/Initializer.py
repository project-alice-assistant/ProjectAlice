VERSION = 1.22

import getpass
import importlib
import json
import logging
import socket
import subprocess
import sys
import time
from pathlib import Path

import os


YAML = '/boot/ProjectAlice.yaml'
ASOUND = '/etc/asound.conf'
SNIPS_TOML = '/etc/snips.toml'
TEMP = Path('/tmp/service')


class InitDict(dict):

	def __init__(self, default: dict):
		super().__init__(default)


	def __getitem__(self, item):
		try:
			return super().__getitem__(item) or ''
		except:
			print(f'Missing key **{item}** in provided yaml file.')
			return ''


class SimpleLogger:

	def __init__(self, prepend: str = None):
		self._prepend = f'[{prepend}]\t '
		self._logger = logging.getLogger('ProjectAlice')


	def logInfo(self, text: str):
		self._logger.info(f'{self._prepend} {text}')


	def logWarning(self, text: str):
		self._logger.warning(f'{self._prepend} {text}')


	def logError(self, text: str):
		self._logger.error(f'{self._prepend} {text}')


	def logFatal(self, text: str):
		self._logger.fatal(f'{self._prepend} {text}')
		exit(1)


class PreInit:
	"""
	Pre init checks and makes sure vital stuff is installed and running. Not much, but internet, venv and so on
	Pre init is meant to run on the system python and not on the venv
	"""

	PIP = './venv/bin/pip'

	def __init__(self):
		self._logger = SimpleLogger(prepend='PreInitializer')

		self.rootDir = Path(__file__).resolve().parent.parent
		self.confsFile = Path(self.rootDir, 'config.py')
		self.initFile = Path(YAML)
		self.initConfs = dict()


	def start(self):
		if not self.initFile.exists() and not self.confsFile.exists():
			self._logger.logFatal('Init file not found and there\'s no configuration file, aborting Project Alice start')
			return False
		elif not self.initFile.exists():
			self._logger.logInfo('No initialization needed')
			return False

		self.initConfs = self.loadConfig()
		self.checkWPASupplicant()
		self.checkInternet()
		self.installSystemDependencies()
		self.doUpdates()
		self.installSystemDependencies()
		if not self.checkVenv():
			self.setServiceFileTo('venv')
			subprocess.run(['sudo', 'systemctl', 'enable', 'ProjectAlice'])
			subprocess.run(['sudo', 'systemctl', 'restart', 'ProjectAlice'])
			exit(0)

		return True


	def installSystemDependencies(self):
		reqs = [line.rstrip('\n') for line in open(Path(self.rootDir, 'sysrequirements.txt'))]
		subprocess.run(['sudo', 'apt-get', 'install', '-y', '--allow-unauthenticated'] + reqs)


	def loadConfig(self) -> dict:

		try:
			import yaml
		except:
			self.setServiceFileTo('system')
			subprocess.run(['sudo', 'systemctl', 'restart', 'ProjectAlice'])
			exit(0)

		with Path(YAML).open(mode='r') as f:
			try:
				# noinspection PyUnboundLocalVariable
				load = yaml.safe_load(f)
				if not load:
					raise yaml.YAMLError

				initConfs = InitDict(load)
			except yaml.YAMLError as e:
				self._logger.logFatal(f'Failed loading init configurations: {e}')
				return dict()

			# Check that we are running using the latest yaml
			if float(initConfs['version']) < VERSION:
				self._logger.logFatal('The yaml file you are using is deprecated. Please update it before trying again')

			return initConfs


	@staticmethod
	def isVenv() -> bool:
		return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)


	def checkWPASupplicant(self):
		wpaSupplicant = Path('/etc/wpa_supplicant/wpa_supplicant.conf')
		if not wpaSupplicant.exists() and self.initConfs['useWifi']:
			self._logger.logInfo('Setting up wifi')

			if not self.initConfs['wifiCountryCode'] or not self.initConfs['wifiNetworkName'] or not self.initConfs['wifiWPAPass']:
				self._logger.logFatal('You must specify the wifi parameters')

			bootWpaSupplicant = Path('/boot/wpa_supplicant.conf')

			wpaFile = Path('wpa_supplicant.conf').read_text() \
				.replace('%wifiCountryCode%', str(self.initConfs['wifiCountryCode'])) \
				.replace('%wifiNetworkName%', str(self.initConfs['wifiNetworkName'])) \
				.replace('%wifiWPAPass%', str(self.initConfs['wifiWPAPass']))

			file = Path(self.rootDir, 'wifi.conf')
			file.write_text(wpaFile)

			subprocess.run(['sudo', 'mv', str(file), bootWpaSupplicant])
			self._logger.logInfo('Successfully initialized wpa_supplicant.conf')
			self.reboot()


	def doUpdates(self):
		subprocess.run(['git', 'config', '--global', 'user.name', '"An Other"'])
		subprocess.run(['git', 'config', '--global', 'user.email', '"anotheruser@projectalice.io"'])

		updateChannel = self.initConfs['aliceUpdateChannel'] if 'aliceUpdateChannel' in self.initConfs else 'master'
		updateSource = self.getUpdateSource(updateChannel)
		# Update our system and sources
		subprocess.run(['sudo', 'apt-get', 'update'])
		subprocess.run(['sudo', 'apt-get', 'dist-upgrade', '-y'])
		subprocess.run(['sudo', 'apt', 'autoremove', '-y'])
		subprocess.run(['git', 'clean', '-df'])
		subprocess.run(['git', 'stash'])

		result = subprocess.run(['git', 'checkout', updateSource], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		if 'switched' in result.stderr.decode().lower():
			print('Switched branch, restarting...')
			self.restart()

		result = subprocess.run(['git', 'pull'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		if 'core/initializer.py' in result.stdout.decode().lower():
			print('Updated critical sources, restarting...')
			self.restart()

		subprocess.run(['git', 'stash', 'clear'])


	@staticmethod
	def reboot():
		time.sleep(1)
		subprocess.run(['sudo', 'shutdown', '-r', 'now'])
		exit(0)


	def restart(self):
		sys.stdout.flush()
		try:
			# Close everything related to ProjectAlice, allows restart without component failing
			try:
				import psutil
			except:
				self.setServiceFileTo('system')
				subprocess.run(['sudo', 'systemctl', 'restart', 'ProjectAlice'])
				exit(0)

			# noinspection PyUnboundLocalVariable
			process = psutil.Process(os.getpid())
			for handler in process.open_files() + process.connections():
				os.close(handler.fd)
		except Exception as e:
			print(f'Failed restarting Project Alice: {e}')

		python = sys.executable
		os.execl(python, python, *sys.argv)


	def checkInternet(self):
		try:
			socket.create_connection(('www.google.com', 80))
			connected = True
		except:
			connected = False

		if not connected:
			self._logger.logFatal('Your device needs internet access to continue')


	def getUpdateSource(self, definedSource: str) -> str:
		updateSource = 'master'
		if definedSource in {'master', 'release'}:
			return updateSource

		try:
			import requests
		except:
			self.setServiceFileTo('system')
			subprocess.run(['sudo', 'systemctl', 'restart', 'ProjectAlice'])
			exit(0)

		# noinspection PyUnboundLocalVariable
		req = requests.get('https://api.github.com/repos/project-alice-assistant/ProjectAlice/branches')
		result = req.json()

		versions = list()
		from core.base.model.Version import Version
		for branch in result:
			repoVersion = Version.fromString(branch['name'])

			releaseType = repoVersion.releaseType
			if not repoVersion.isVersionNumber \
					or definedSource == 'rc' and releaseType in {'b', 'a'} \
					or definedSource == 'beta' and releaseType == 'a':
				continue

			versions.append(repoVersion)

		if versions:
			versions.sort(reverse=True)
			updateSource = versions[0]

		return str(updateSource)


	def checkVenv(self) -> bool:
		if not Path('venv').exists():
			self._logger.logInfo('Not running with venv, I need to create it')
			subprocess.run(['sudo', 'apt-get', 'install', 'python3-venv', '-y'])
			subprocess.run(['python3.7', '-m', 'venv', 'venv'])
			self.updateVenv()
			self._logger.logInfo('Installed virtual environement, restarting...')
			return False
		elif not self.isVenv():
			self.updateVenv()
			self._logger.logWarning('Restarting to run using virtual environement: "./venv/bin/python main.py"')
			return False

		return True


	def updateVenv(self):
		subprocess.run([self.PIP, 'uninstall', '-y', '-r', str(Path(self.rootDir, 'pipuninstalls.txt'))])
		subprocess.run([self.PIP, 'install', '-r', str(Path(self.rootDir, 'requirements.txt'))])


	@staticmethod
	def setServiceFileTo(pointer: str):
		serviceFilePath = Path('/etc/systemd/system/ProjectAlice.service')
		if serviceFilePath.exists():
			subprocess.run(['sudo', 'rm', serviceFilePath])

		serviceFile = Path('ProjectAlice.service').read_text()

		if pointer == 'venv':
			serviceFile = serviceFile.replace('#EXECSTART', f'ExecStart=/home/{getpass.getuser()}/ProjectAlice/venv/bin/python main.py')
		else:
			serviceFile = serviceFile.replace('#EXECSTART', f'ExecStart=python3 main.py')

		serviceFile = serviceFile.replace('#WORKINGDIR', f'WorkingDirectory=/home/{getpass.getuser()}/ProjectAlice')
		serviceFile = serviceFile.replace('#USER', f'User={getpass.getuser()}')
		TEMP.write_text(serviceFile)
		subprocess.run(['sudo', 'mv', TEMP, serviceFilePath])
		subprocess.run(['sudo', 'systemctl', 'daemon-reload'])
		time.sleep(1)


class Initializer:
	PIP = './venv/bin/pip'

	def __init__(self):
		super().__init__()
		self._logger = SimpleLogger('Initializer')
		self._logger.logInfo('Starting Project Alice initialization')
		self._preInit = PreInit()
		self._confsSample = Path(self._preInit.rootDir, 'configTemplate.py')
		self._confsFile = self._preInit.confsFile
		self._rootDir = self._preInit.rootDir


	def initProjectAlice(self) -> bool:  # NOSONAR
		if not self._preInit.start():
			return False

		initConfs = self._preInit.initConfs

		if 'forceRewrite' not in initConfs:
			initConfs['forceRewrite'] = True

		if not self._confsFile.exists() and not self._confsSample.exists():
			self._logger.logFatal('No config and no config template found, can\'t continue')

		elif not self._confsFile.exists() and self._confsSample.exists():
			self._logger.logWarning('No config file found, creating it from sample file')
			confs = self.newConfs()
			self._confsFile.write_text(f"settings = {json.dumps(confs, indent=4).replace('false', 'False').replace('true', 'True')}")

		elif self._confsFile.exists() and not initConfs['forceRewrite']:
			self._logger.logWarning('Config file already existing and user not wanting to rewrite, aborting')
			return False

		elif self._confsFile.exists() and initConfs['forceRewrite']:
			self._logger.logWarning('Config file found and force rewrite specified, let\'s restart all this!')
			confs = self.newConfs()
			self._confsFile.write_text(f"settings = {json.dumps(confs, indent=4).replace('false', 'False').replace('true', 'True')}")

		try:
			# noinspection PyUnresolvedReferences
			import config
		except:
			config = importlib.import_module('config')

		# noinspection PyUnresolvedReferences
		confs = config.settings.copy()


		subprocess.run(['sudo', 'apt', 'install', '-y', f'./system/snips/snips-platform-common_0.64.0_armhf.deb'])
		subprocess.run(['sudo', 'apt', 'install', '-y', f'./system/snips/snips-nlu_0.64.0_armhf.deb'])
		subprocess.run(['sudo', 'systemctl', 'stop', 'snips-nlu'])
		subprocess.run(['sudo', 'systemctl', 'disable', 'snips-nlu'])
		subprocess.run(['sudo', 'apt', 'install', '-y', f'./system/snips/snips-hotword_0.64.0_armhf.deb'])
		subprocess.run(['sudo', 'systemctl', 'stop', 'snips-hotword'])
		subprocess.run(['sudo', 'systemctl', 'disable', 'snips-hotword'])
		subprocess.run(['sudo', 'apt', 'install', '-y', f'./system/snips/snips-hotword-model-heysnipsv4_0.64.0_armhf.deb'])

		subprocess.run(['wget', 'http://ftp.us.debian.org/debian/pool/non-free/s/svox/libttspico0_1.0+git20130326-9_armhf.deb'])
		subprocess.run(['wget', 'http://ftp.us.debian.org/debian/pool/non-free/s/svox/libttspico-utils_1.0+git20130326-9_armhf.deb'])
		subprocess.run(['sudo', 'apt', 'install', '-y', './libttspico0_1.0+git20130326-9_armhf.deb', './libttspico-utils_1.0+git20130326-9_armhf.deb'])

		subprocess.run(['rm', 'libttspico0_1.0+git20130326-9_armhf.deb'])
		subprocess.run(['rm', 'libttspico-utils_1.0+git20130326-9_armhf.deb'])

		confPath = Path('/etc/mosquitto/conf.d/websockets.conf')
		if not confPath.exists():
			subprocess.run(['sudo', 'cp', str(Path(self._rootDir, 'system/websockets.conf')), str(confPath)])

		subprocess.run(['sudo', 'systemctl', 'stop', 'mosquitto'])
		subprocess.run(['sudo', 'sed', '-i', '-e', 's/persistence true/persistence false/', '/etc/mosquitto/mosquitto.conf'])
		subprocess.run(['sudo', 'rm', '/var/lib/mosquitto/mosquitto.db '])

		# Now let's dump some values to their respective places
		# First those that need some checks and self filling in case unspecified
		confs['mqttHost'] = str(initConfs['mqttHost']) or 'localhost'
		confs['mqttPort'] = initConfs['mqttPort'] or 1883

		pinCode = initConfs['adminPinCode']
		try:
			pin = int(pinCode)
			if len(str(pin)) != 4:
				raise Exception
		except:
			self._logger.logFatal('Pin code must be 4 digits')

		confs['adminPinCode'] = int(pinCode)

		confs['stayCompletlyOffline'] = bool(initConfs['stayCompletlyOffline'] or False)
		if confs['stayCompletlyOffline']:
			confs['keepASROffline'] = True
			confs['keepTTSOffline'] = True
			confs['skillAutoUpdate'] = False
			confs['asr'] = 'deepspeech'
			confs['tts'] = 'pico'
			confs['awsRegion'] = ''
			confs['awsAccessKey'] = ''
			confs['awsSecretKey'] = ''
		else:
			confs['keepASROffline'] = bool(initConfs['keepASROffline'])
			confs['keepTTSOffline'] = bool(initConfs['keepTTSOffline'])
			confs['skillAutoUpdate'] = bool(initConfs['skillAutoUpdate'])
			confs['tts'] = initConfs['tts'] if initConfs['tts'] in {'pico', 'mycroft', 'amazon', 'google', 'watson'} else 'pico'
			confs['awsRegion'] = initConfs['awsRegion']
			confs['awsAccessKey'] = initConfs['awsAccessKey']
			confs['awsSecretKey'] = initConfs['awsSecretKey']

			confs['asr'] = initConfs['asr'] if initConfs['asr'] in {'pocketsphinx', 'google', 'deepspeech', 'snips'} else 'deepspeech'
			if confs['asr'] == 'google' and not initConfs['googleServiceFile']:
				self._logger.logInfo('You cannot use Google Asr without a google service file, falling back to Deepspeech')
				confs['asr'] = 'deepspeech'

			if confs['asr'] == 'snips' and confs['activeLanguage'] != 'en':
				self._logger.logInfo('You can only use Snips Asr for english, falling back to Deepspeech')
				confs['asr'] = 'deepspeech'

			if initConfs['googleServiceFile']:
				googleCreds = Path(self._rootDir, 'credentials/googlecredentials.json')
				googleCreds.write_text(json.dumps(initConfs['googleServiceFile']))

		# Those that don't need checking
		confs['ssid'] = initConfs['wifiNetworkName']
		confs['wifipassword'] = str(initConfs['wifiWPAPass'])
		confs['useHLC'] = bool(initConfs['useHLC'])
		confs['webInterfaceActive'] = bool(initConfs['webInterfaceActive'])
		confs['devMode'] = bool(initConfs['devMode'])
		confs['newDeviceBroadcastPort'] = int(initConfs['newDeviceBroadcastPort'] or 12354)
		confs['activeLanguage'] = initConfs['activeLanguage'] if initConfs['activeLanguage'] in {'en', 'de', 'fr'} else 'en'
		confs['activeCountryCode'] = initConfs['activeCountryCode'] or 'US'
		confs['baseCurrency'] = initConfs['baseCurrency'] or 'USD'
		confs['baseUnits'] = initConfs['baseUnits'] if initConfs['baseUnits'] in {'metric', 'kelvin', 'imperial'} else 'metric'
		confs['enableDataStoring'] = bool(initConfs['enableDataStoring'])
		confs['autoPruneStoredData'] = initConfs['autoPruneStoredData'] or 1000
		confs['probabilityThreshold'] = float(initConfs['probabilityThreshold'] or 0.5)
		confs['shortReplies'] = bool(initConfs['shortReplies'])
		confs['whisperWhenSleeping'] = bool(initConfs['whisperWhenSleeping'])
		confs['ttsLanguage'] = initConfs['ttsLanguage']
		confs['ttsType'] = initConfs['ttsType']
		confs['ttsVoice'] = initConfs['ttsVoice']
		confs['githubUsername'] = initConfs['githubUsername']
		confs['githubToken'] = initConfs['githubToken']
		confs['timezone'] = initConfs['timezone'] or 'Europe/Zurich'

		aliceUpdateChannel = initConfs['aliceUpdateChannel']
		if aliceUpdateChannel not in {'master', 'rc', 'beta', 'alpha'}:
			self._logger.logWarning(f'{aliceUpdateChannel} is not a supported updateChannel, only master, rc, beta and alpha are supported. Reseting to master')
			confs['aliceUpdateChannel'] = 'master'
		else:
			confs['aliceUpdateChannel'] = aliceUpdateChannel

		skillsUpdateChannel = initConfs['skillsUpdateChannel'] if 'skillsUpdateChannel' in initConfs else 'master'
		if skillsUpdateChannel not in {'master', 'rc', 'beta', 'alpha'}:
			self._logger.logWarning(f'{skillsUpdateChannel} is not a supported updateChannel, only master, rc, beta and alpha are supported. Reseting to master')
			confs['skillsUpdateChannel'] = 'master'
		else:
			confs['skillsUpdateChannel'] = skillsUpdateChannel

		confs['mqtt_username'] = str(initConfs['mqttUser'])
		confs['mqttPassword'] = str(initConfs['mqttPassword'])
		confs['mqttTLSFile'] = initConfs['mqttTLSFile']

		try:
			import pkg_resources

			pkg_resources.require('snips-nlu')
			subprocess.run(['./venv/bin/snips-nlu', 'download', confs['activeLanguage']])
		except:
			self._logger.logInfo("Snips NLU not installed, let's do this")
			subprocess.run(['sudo', 'apt-get', 'install', 'libatlas3-base', 'libgfortran5'])
			subprocess.run(['wget', '--content-disposition', 'https://github.com/project-alice-assistant/snips-nlu-rebirth/blob/master/wheels/scikit_learn-0.22.1-cp37-cp37m-linux_armv7l.whl?raw=true'])
			subprocess.run(['wget', '--content-disposition', 'https://github.com/project-alice-assistant/snips-nlu-rebirth/blob/master/wheels/scipy-1.3.3-cp37-cp37m-linux_armv7l.whl?raw=true'])
			subprocess.run(['wget', '--content-disposition', 'https://github.com/project-alice-assistant/snips-nlu-rebirth/blob/master/wheels/snips_nlu_utils-0.9.1-cp37-cp37m-linux_armv7l.whl?raw=true'])
			subprocess.run(['wget', '--content-disposition', 'https://github.com/project-alice-assistant/snips-nlu-rebirth/blob/master/wheels/snips_nlu_parsers-0.4.3-cp37-cp37m-linux_armv7l.whl?raw=true'])
			subprocess.run(['wget', '--content-disposition', 'https://github.com/project-alice-assistant/snips-nlu-rebirth/blob/master/wheels/snips_nlu-0.20.2-py3-none-any.whl?raw=true'])
			time.sleep(1)
			subprocess.run([self.PIP, 'install', 'scipy-1.3.3-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run([self.PIP, 'install', 'scikit_learn-0.22.1-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run([self.PIP, 'install', 'snips_nlu_utils-0.9.1-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run([self.PIP, 'install', 'snips_nlu_parsers-0.4.3-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run([self.PIP, 'install', 'snips_nlu-0.20.2-py3-none-any.whl'])
			time.sleep(1)
			subprocess.run(['rm', 'scipy-1.3.3-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run(['rm', 'scikit_learn-0.22.1-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run(['rm', 'snips_nlu_utils-0.9.1-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run(['rm', 'snips_nlu_parsers-0.4.3-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run(['rm', 'snips_nlu-0.20.2-py3-none-any.whl'])
			subprocess.run(['./venv/bin/snips-nlu', 'download', confs['activeLanguage']])

		snipsConf = self.loadSnipsConfigurations()
		if not snipsConf:
			self._logger.logFatal('Error loading snips.toml')

		if initConfs['mqttHost'] != 'localhost' or initConfs['mqttPort'] != 1883:
			snipsConf['snips-common']['mqtt'] = f'{initConfs["mqttHost"]}:{initConfs["mqttPort"]}'

		if initConfs['mqttUser']:
			snipsConf['snips-common']['mqtt_username'] = initConfs['mqttUser']
			snipsConf['snips-common']['mqtt_password'] = initConfs['mqttPassword']

		snipsConf['snips-common']['assistant'] = f'/home/{getpass.getuser()}/ProjectAlice/assistant'
		snipsConf['snips-hotword']['model'] = [f'/home/{getpass.getuser()}/ProjectAlice/trained/hotwords/snips_hotword/hey_snips=0.53']

		self._logger.logInfo('Installing audio hardware')
		audioHardware = ''
		for hardware in initConfs['audioHardware']:
			if initConfs['audioHardware'][hardware]:
				audioHardware = hardware
				break

		hlcServiceFilePath = Path('/etc/systemd/system/hermesledcontrol.service')
		if initConfs['useHLC']:

			hlcDir = Path('/home', getpass.getuser(), 'hermesLedControl')

			if not hlcDir.exists():
				subprocess.run(['git', 'clone', 'https://github.com/project-alice-assistant/hermesLedControl.git', str(Path('/home', getpass.getuser(), 'hermesLedControl'))])
			else:
				subprocess.run(['git', '-C', hlcDir, 'stash'])
				subprocess.run(['git', '-C', hlcDir, 'pull'])
				subprocess.run(['git', '-C', hlcDir, 'stash', 'clear'])

			if hlcServiceFilePath.exists():
				subprocess.run(['sudo', 'rm', hlcServiceFilePath])

			subprocess.run(['python3.7', '-m', 'venv', f'/home/{getpass.getuser()}/hermesLedControl/venv'])

			reqs = [
				'RPi.GPIO',
				'spidev',
				'gpiozero',
				'paho-mqtt',
				'toml',
				'numpy'
			]
			for req in reqs:
				subprocess.run([f'/home/{getpass.getuser()}/hermesLedControl/venv/bin/pip', 'install', req])

			serviceFile = Path(f'/home/{getpass.getuser()}/hermesLedControl/hermesledcontrol.service').read_text()
			serviceFile = serviceFile.replace('%WORKING_DIR%', f'/home/{getpass.getuser()}/hermesLedControl')
			serviceFile = serviceFile.replace('%EXECSTART%', f'/home/{getpass.getuser()}/hermesLedControl/venv/bin/python main.py --hardware=%HARDWARE% --pattern=projectalice')
			serviceFile = serviceFile.replace('%USER%', f'{getpass.getuser()}')

			TEMP.write_text(serviceFile)
			subprocess.run(['sudo', 'mv', TEMP, hlcServiceFilePath])

		useFallbackHLC = False
		if audioHardware in {'respeaker2', 'respeaker4', 'respeaker6MicArray'}:
			subprocess.run(['sudo', Path(self._rootDir, 'system/scripts/audioHardware/respeakers.sh')])
			if initConfs['useHLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', f's/%HARDWARE%/{audioHardware}/', str(hlcServiceFilePath)])

			settings = Path(f'system/asounds/{audioHardware.lower()}.conf').read_text()
			confs['asoundConfig'] = settings

			dest = Path('/etc/voicecard/asound_2mic.conf')
			if audioHardware == 'respeaker4':
				dest = Path('/etc/voicecard/asound_4mic.conf')
			elif audioHardware == 'respeaker6MicArray':
				dest = Path('/etc/voicecard/asound_6mic.conf')

			subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system', 'asounds', f'{audioHardware.lower()}.conf'), dest])
			subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system', 'asounds', f'{audioHardware.lower()}.conf'), Path(ASOUND)])

		elif audioHardware == 'respeaker7':
			subprocess.run(['sudo', Path(self._rootDir, 'system/scripts/audioHardware/respeaker7.sh')])
			if initConfs['useHLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', 's/%HARDWARE%/respeaker7MicArray/', str(hlcServiceFilePath)])

		elif audioHardware == 'respeakerCoreV2':
			subprocess.run(['sudo', Path(self._rootDir, 'system/scripts/audioHardware/respeakerCoreV2.sh')])
			if initConfs['useHLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', f's/%HARDWARE%/{audioHardware}/', str(hlcServiceFilePath)])

		elif audioHardware in {'matrixCreator', 'matrixVoice'}:
			subprocess.run(['sudo', Path(self._rootDir, 'system/scripts/audioHardware/matrix.sh')])
			subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system', 'asounds', 'matrix.conf'), Path(ASOUND)])

			settings = Path(f'system/asounds/matrix.conf').read_text()
			confs['asoundConfig'] = settings

			if initConfs['useHLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', f's/%HARDWARE%/{audioHardware.lower()}/', str(hlcServiceFilePath)])

		elif audioHardware == 'googleAIY':
			subprocess.run(['sudo', Path(self._rootDir, 'system/scripts/audioHardware/aiy.sh')])
			if initConfs['useHLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', 's/%HARDWARE%/googleAIY/', str(hlcServiceFilePath)])

			subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system', 'asounds', 'aiy.conf'), Path(ASOUND)])
			settings = Path(f'system/asounds/aiy.conf').read_text()
			confs['asoundConfig'] = settings

		elif audioHardware == 'usbMic':
			subprocess.run(['sudo', Path(self._rootDir, 'system/scripts/audioHardware/usbmic.sh')])
			subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system', 'asounds', 'usbmic.conf'), Path(ASOUND)])

			settings = Path(f'system/asounds/usbmic.conf').read_text()
			confs['asoundConfig'] = settings

			useFallbackHLC = True

		elif audioHardware == 'ps3eye':
			subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system', 'asounds', 'ps3eye.conf'), Path(ASOUND)])
			asoundrc = f'/home/{getpass.getuser()}/.asoundrc'
			subprocess.run(['echo', 'pcm.dsp0 {', '>', asoundrc])
			subprocess.run(['echo', '    type plug', '>>', asoundrc])
			subprocess.run(['echo', '    slave.pcm "dmix"', '>>', asoundrc])
			subprocess.run(['echo', '}', '>>', asoundrc])

			settings = Path(f'system/asounds/ps3eye.conf').read_text()
			confs['asoundConfig'] = settings

			useFallbackHLC = True

		elif audioHardware == 'jabra410':
			subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system', 'asounds', 'jabra410.conf'), Path(ASOUND)])

			settings = Path(f'system/asounds/jabra410.conf').read_text()
			confs['asoundConfig'] = settings

			useFallbackHLC = True

		if initConfs['useHLC'] and useFallbackHLC:
			subprocess.run(['sudo', 'sed', '-i', '-e', 's/%HARDWARE%/dummy/', str(hlcServiceFilePath)])

		sort = dict(sorted(confs.items()))

		try:
			confString = json.dumps(sort, indent=4).replace('false', 'False').replace('true', 'True')
			self._confsFile.write_text(f'settings = {confString}')
		except Exception as e:
			self._logger.logFatal(f'An error occured while writting final configuration file: {e}')
		else:
			importlib.reload(config)

		import toml
		TEMP.write_text(toml.dumps(snipsConf))
		subprocess.run(['sudo', 'mv', TEMP, Path(SNIPS_TOML)])

		subprocess.run(['sudo', 'rm', '-rf', Path(self._rootDir, 'assistant')])

		subprocess.run(['sudo', 'sed', '-i', '-e', 's/#dtparam=i2c_arm=on/dtparam=i2c_arm=on/', '/boot/config.txt'])
		subprocess.run(['sudo', 'sed', '-i', '-e', 's/#dtparam=spi=on/dtparam=spi=on/', '/boot/config.txt'])

		subprocess.run(['sudo', 'timedatectl', 'set-timezone', confs['timezone']])

		if initConfs['keepYAMLBackup']:
			subprocess.run(['sudo', 'mv', Path(YAML), Path('/boot/ProjectAlice.yaml.bak')])
		else:
			subprocess.run(['sudo', 'rm', Path(YAML)])

		subprocess.run(['sudo', 'systemctl', 'daemon-reload'])
		subprocess.run(['sudo', 'systemctl', 'enable', 'ProjectAlice'])
		if initConfs['useHLC']:
			subprocess.run(['sudo', 'systemctl', 'enable', hlcServiceFilePath.stem])

		self._logger.logWarning('Initializer done with configuring')
		time.sleep(2)
		subprocess.run(['sudo', 'shutdown', '-r', 'now'])


	def loadSnipsConfigurations(self) -> dict:
		self._logger.logInfo('Loading Snips configuration file')
		snipsConfig = Path(SNIPS_TOML)

		if snipsConfig.exists():
			subprocess.run(['sudo', 'rm', SNIPS_TOML])

		subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system/snips/snips.toml'), Path(SNIPS_TOML)])

		import toml
		return toml.load(snipsConfig)


	@staticmethod
	def newConfs():
		import configTemplate
		return {configName: configData['defaultValue'] for configName, configData in configTemplate.settings.items()}
