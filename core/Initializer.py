import getpass
import importlib
import json
import socket
import subprocess
import time
from pathlib import Path

import pkg_resources
import requests

from core.base.model.TomlFile import TomlFile
from core.base.model.Version import Version

PIP = './venv/bin/pip'
YAML = '/boot/ProjectAlice.yaml'
ASOUND = '/etc/asound.conf'
SNIPS_TOML = '/etc/snips.toml'

try:
	import yaml
except:
	subprocess.run([PIP, 'install', 'pyyaml'])
	import yaml

import configTemplate
from core.base.model.ProjectAliceObject import ProjectAliceObject


class InitDict(dict):

	def __init__(self, default: dict):
		super().__init__(default)


	def __getitem__(self, item):
		try:
			return super().__getitem__(item) or ''
		except:
			print(f'Missing key **{item}** in provided yaml file.')
			return ''


class Initializer(ProjectAliceObject):
	NAME = 'ProjectAlice'

	_WPA_FILE = '''country=%wifiCountryCode%
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="%wifiNetworkName%"
    scan_ssid=1
    psk="%wifiWPAPass%"
    key_mgmt=WPA-PSK
}
	'''


	def __init__(self):
		super().__init__()
		self.logInfo('Starting Project Alice initialization')

		self._rootDir = Path(__file__).resolve().parent.parent

		self._confsFile = Path(self._rootDir, 'config.py')
		self._confsSample = Path(self._rootDir, 'configTemplate.py')
		self._initFile = Path(YAML)
		self._latest = 1.18


	def initProjectAlice(self) -> bool:
		if not self._initFile.exists() and not self._confsFile.exists():
			self.logFatal('Init file not found and there\'s no configuration file, aborting Project Alice start')
		elif not self._initFile.exists():
			self.logInfo('No initialization needed')
			return False

		with self._initFile.open(mode='r') as f:
			try:
				load = yaml.safe_load(f)
				if not load:
					raise yaml.YAMLError

				initConfs = InitDict(load)
			except yaml.YAMLError as e:
				self.logFatal(f'Failed loading init configurations: {e}')

		# Check that we are running using the latest yaml
		if float(initConfs['version']) < self._latest:
			self.logFatal('The yaml file you are using is deprecated. Please update it before trying again')

		wpaSupplicant = Path('/etc/wpa_supplicant/wpa_supplicant.conf')
		if not wpaSupplicant.exists() and initConfs['useWifi']:
			self.logInfo('Setting up wifi')

			if not initConfs['wifiCountryCode'] or not initConfs['wifiNetworkName'] or not initConfs['wifiWPAPass']:
				self.logFatal('You must specify the wifi parameters')

			bootWpaSupplicant = Path('/boot/wpa_supplicant.conf')

			wpaFile = self._WPA_FILE \
				.replace('%wifiCountryCode%', str(initConfs['wifiCountryCode'])) \
				.replace('%wifiNetworkName%', str(initConfs['wifiNetworkName'])) \
				.replace('%wifiWPAPass%', str(initConfs['wifiWPAPass']))

			file = Path(self._rootDir, 'wifi.conf')
			file.write_text(wpaFile)

			subprocess.run(['sudo', 'mv', str(file), bootWpaSupplicant])
			self.logInfo('Successfully initialized wpa_supplicant.conf')
			time.sleep(1)
			subprocess.run(['sudo', 'shutdown', '-r', 'now'])
			exit(0)

		try:
			socket.create_connection(('www.google.com', 80))
			connected = True
		except:
			connected = False

		if not connected:
			self.logFatal('Your device needs internet access to continue')

		updateChannel = initConfs['aliceUpdateChannel'] if 'aliceUpdateChannel' in initConfs else 'master'
		updateSource = self.getUpdateSource(updateChannel)
		# Update our system and sources
		subprocess.run(['sudo', 'apt-get', 'update'])
		subprocess.run(['sudo', 'apt-get', 'dist-upgrade', '-y'])
		subprocess.run(['git', 'clean', '-df'])
		subprocess.run(['git', 'stash'])
		subprocess.run(['git', 'checkout', updateSource])
		subprocess.run(['git', 'pull'])
		subprocess.run(['git', 'stash', 'clear'])

		time.sleep(1)

		subprocess.run([PIP, 'uninstall', '-y', '-r', str(Path(self._rootDir, 'pipuninstalls.txt'))])

		if 'forceRewrite' not in initConfs:
			initConfs['forceRewrite'] = True

		if not self._confsFile.exists() and not self._confsSample.exists():
			self.logFatal('No config and no config template found, can\'t continue')

		elif not self._confsFile.exists() and self._confsSample.exists():
			self.logWarning('No config file found, creating it from sample file')
			confs = self.newConfs()
			self._confsFile.write_text(f"settings = {json.dumps(confs, indent=4).replace('false', 'False').replace('true', 'True')}")

		elif self._confsFile.exists() and not initConfs['forceRewrite']:
			self.logWarning('Config file already existing and user not wanting to rewrite, aborting')
			return False

		elif self._confsFile.exists() and initConfs['forceRewrite']:
			self.logWarning('Config file found and force rewrite specified, let\'s restart all this!')
			self._confsFile.unlink()
			confs = self.newConfs()
			self._confsFile.write_text(f"settings = {json.dumps(confs, indent=4).replace('false', 'False').replace('true', 'True')}")

		config = importlib.import_module('config')
		confs = config.settings.copy()

		# Do some installation if wanted by the user
		if 'doGroundInstall' not in initConfs or initConfs['doGroundInstall']:
			subprocess.run([PIP, 'install', '-r', str(Path(self._rootDir, 'requirements.txt'))])

			if 'installOnBuster' not in initConfs or initConfs['installOnBuster']:
				subprocess.run(['sudo', 'apt-get', 'install', '-y', 'dirmngr', 'apt-transport-https'])
				subprocess.run(['sudo', 'bash', '-c', 'echo "deb https://raspbian.snips.ai/stretch stable main" > /etc/apt/sources.list.d/snips.list'])
				subprocess.run(['sudo', 'apt-key', 'adv', '--fetch-keys', 'https://debian.snips.ai/5FFCD0DEB5BA45CD.pub'])
				subprocess.run(['wget', '-q', 'https://ftp-master.debian.org/keys/release-10.asc', '-O-', '|', 'sudo', 'apt-key', 'add', '-'])
				subprocess.run(['echo', '"deb http://deb.debian.org/debian buster non-free"', '|', 'sudo', 'tee', '/etc/apt/sources.list.d/debian.list'])
				subprocess.run(['sudo', 'apt-key', 'adv', '--keyserver', 'gpg.mozilla.org', '--recv-keys', 'D4F50CDCA10A2849'])
				subprocess.run(['sudo', 'sh', '-c', '\'curl https://raspbian.snips.ai/531DD1A7B702B14D.pub | apt-key add -\''])
				subprocess.run(['sudo', 'apt-get', 'install', '-y', 'libttspico0'])
				subprocess.run(['sudo', 'apt-get', 'install', '-y', 'libttspico-utils'])
				subprocess.run(['sudo', 'apt-get', 'install', '-y', 'libatlas3-base=3.10.3-8+rpi1'])
				subprocess.run(['sudo', 'apt-get', 'install', '-y', 'libgfortran3'])
			else:
				subprocess.run(['sudo', 'bash', '-c', 'echo "deb https://raspbian.snips.ai/$(lsb_release -cs) stable main" > /etc/apt/sources.list.d/snips.list'])
				subprocess.run(['sudo', 'apt-key', 'adv', '--keyserver', 'gpg.mozilla.org', '--recv-keys', 'D4F50CDCA10A2849'])
				subprocess.run(['sudo', 'apt-get', 'update'])

			reqs = [line.rstrip('\n') for line in open(Path(self._rootDir, 'sysrequirements.txt'))]
			subprocess.run(['sudo', 'apt-get', 'install', '-y', '--allow-unauthenticated'] + reqs)

			subprocess.run(['sudo', 'systemctl', 'stop', 'snips-*'])
			subprocess.run(['sudo', 'systemctl', 'disable', 'snips-nlu'])
			subprocess.run(['sudo', 'systemctl', 'disable', 'snips-dialogue'])
			subprocess.run(['sudo', 'systemctl', 'disable', 'snips-injection'])
			subprocess.run(['sudo', 'systemctl', 'disable', 'snips-hotword'])
			subprocess.run(['sudo', 'systemctl', 'disable', 'snips-audio-server'])
			subprocess.run(['sudo', 'systemctl', 'disable', 'snips-tts'])

		confPath = Path('/etc/mosquitto/conf.d/websockets.conf')
		if not confPath.exists():
			subprocess.run(['sudo', 'cp', str(Path(self._rootDir, 'system/websockets.conf')), str(confPath)])
			subprocess.run(['sudo', 'systemctl', 'restart', 'mosquitto'])

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
			self.logFatal('Pin code must be 4 digits')

		confs['adminPinCode'] = int(pinCode)

		confs['stayCompletlyOffline'] = bool(initConfs['stayCompletlyOffline'])
		if initConfs['stayCompletlyOffline']:
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
			confs['tts'] = initConfs['tts'] if initConfs['tts'] in {'pico', 'snips', 'mycroft', 'amazon', 'google'} else 'pico'
			confs['awsRegion'] = initConfs['awsRegion']
			confs['awsAccessKey'] = initConfs['awsAccessKey']
			confs['awsSecretKey'] = initConfs['awsSecretKey']

			confs['asr'] = initConfs['asr'] if initConfs['asr'] in {'pocketsphinx', 'google', 'deepspeech'} else 'deepspeech'
			if confs['asr'] == 'google' and not initConfs['googleServiceFile']:
				self.logInfo('You cannot use Google ASR without a google service file, falling back to Deepspeech')
				confs['asr'] = 'deepspeech'

			if initConfs['googleServiceFile']:
				googleCreds = Path(self._rootDir, 'credentials/googlecredentials.json')
				googleCreds.write_text(json.dumps(initConfs['googleServiceFile']))


		# Those that don't need checking
		confs['ssid'] = initConfs['wifiNetworkName']
		confs['wifipassword'] = str(initConfs['wifiWPAPass'])
		confs['micSampleRate'] = int(initConfs['micSampleRate'] or 16000)
		confs['micChannels'] = int(initConfs['micChannels'] or 1)
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
		confs['ttsLanguage'] = initConfs['ttsLanguage'] or confs['activeLanguage']
		confs['ttsType'] = initConfs['ttsType'] if initConfs['ttsType'] in {'female', 'male'} else 'female'
		confs['ttsVoice'] = initConfs['ttsVoice']
		confs['githubUsername'] = initConfs['githubUsername']
		confs['githubToken'] = initConfs['githubToken']

		aliceUpdateChannel = initConfs['aliceUpdateChannel']
		if aliceUpdateChannel not in {'master', 'rc', 'beta', 'alpha'}:
			self.logWarning(f'{aliceUpdateChannel} is not a supported updateChannel, only master, rc, beta and alpha are supported. Reseting to master')
			confs['aliceUpdateChannel'] = 'master'
		else:
			confs['aliceUpdateChannel'] = aliceUpdateChannel

		skillsUpdateChannel = initConfs['skillsUpdateChannel'] if 'skillsUpdateChannel' in initConfs else 'master'
		if skillsUpdateChannel not in {'master', 'rc', 'beta', 'alpha'}:
			self.logWarning(f'{skillsUpdateChannel} is not a supported updateChannel, only master, rc, beta and alpha are supported. Reseting to master')
			confs['skillsUpdateChannel'] = 'master'
		else:
			confs['skillsUpdateChannel'] = skillsUpdateChannel

		confs['mqtt_username'] = str(initConfs['mqttUser'])
		confs['mqttPassword'] = str(initConfs['mqttPassword'])
		confs['mqttTLSFile'] = initConfs['mqttTLSFile']

		try:
			pkg_resources.require('snips-nlu')
			subprocess.run(['./venv/bin/snips-nlu', 'download', confs['activeLanguage']])
		except:
			self.logInfo("Snips NLU not installed, let's do this")
			subprocess.run(['sudo', 'apt-get', 'install', 'libatlas3-base', 'libgfortran5'])
			subprocess.run(['wget', '--content-disposition', 'https://github.com/project-alice-assistant/snips-nlu-rebirth/blob/master/wheels/scikit_learn-0.22.1-cp37-cp37m-linux_armv7l.whl?raw=true'])
			subprocess.run(['wget', '--content-disposition', 'https://github.com/project-alice-assistant/snips-nlu-rebirth/blob/master/wheels/scipy-1.3.3-cp37-cp37m-linux_armv7l.whl?raw=true'])
			subprocess.run(['wget', '--content-disposition', 'https://github.com/project-alice-assistant/snips-nlu-rebirth/blob/master/wheels/snips_nlu_utils-0.9.1-cp37-cp37m-linux_armv7l.whl?raw=true'])
			subprocess.run(['wget', '--content-disposition', 'https://github.com/project-alice-assistant/snips-nlu-rebirth/blob/master/wheels/snips_nlu_parsers-0.4.3-cp37-cp37m-linux_armv7l.whl?raw=true'])
			subprocess.run(['wget', '--content-disposition', 'https://github.com/project-alice-assistant/snips-nlu-rebirth/blob/master/wheels/snips_nlu-0.20.2-py3-none-any.whl?raw=true'])
			time.sleep(1)
			subprocess.run([PIP, 'install', 'scipy-1.3.3-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run([PIP, 'install', 'scikit_learn-0.22.1-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run([PIP, 'install', 'snips_nlu_utils-0.9.1-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run([PIP, 'install', 'snips_nlu_parsers-0.4.3-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run([PIP, 'install', 'snips_nlu-0.20.2-py3-none-any.whl'])
			time.sleep(1)
			subprocess.run(['rm', 'scipy-1.3.3-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run(['rm', 'scikit_learn-0.22.1-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run(['rm', 'snips_nlu_utils-0.9.1-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run(['rm', 'snips_nlu_parsers-0.4.3-cp37-cp37m-linux_armv7l.whl'])
			subprocess.run(['rm', 'snips_nlu-0.20.2-py3-none-any.whl'])
			subprocess.run(['./venv/bin/snips-nlu', 'download', confs['activeLanguage']])

		snipsConf = self.loadSnipsConfigurations()
		if not snipsConf:
			self.logFatal('Error loading snips.toml')

		if initConfs['deviceName'] != 'default':
			snipsConf['snips-audio-server']['bind'] = f'{initConfs["deviceName"]}@mqtt'

		if initConfs['mqttHost'] != 'localhost' or initConfs['mqttPort'] != 1883:
			snipsConf['snips-common']['mqtt'] = f'{initConfs["mqttHost"]}:{initConfs["mqttPort"]}'

		if initConfs['mqttUser']:
			snipsConf['snips-common']['mqtt_username'] = initConfs['mqttUser']
			snipsConf['snips-common']['mqtt_password'] = initConfs['mqttPassword']

		snipsConf['snips-common']['assistant'] = f'/home/{getpass.getuser()}/ProjectAlice/assistant'
		snipsConf['snips-dialogue']['session_timeout'] = 30
		snipsConf['snips-dialogue']['lambda_timeout'] = 10
		snipsConf['snips-dialogue']['retry_count'] = 0
		snipsConf['snips-hotword']['model'] = [f'/home/{getpass.getuser()}/ProjectAlice/trained/hotwords/snips_hotword=0.53']
		snipsConf['snips-hotword']['vad_messages'] = True

		serviceFilePath = Path('/etc/systemd/system/ProjectAlice.service')
		if serviceFilePath.exists():
			subprocess.run(['sudo', 'rm', serviceFilePath])

		serviceFile = Path('ProjectAlice.service').read_text()
		serviceFile.replace('#WORKINGDIR', f'WorkingDirectory=/home/{getpass.getuser()}/ProjectAlice')
		serviceFile.replace('#EXECSTART', f'ExecStart=/home/{getpass.getuser()}/ProjectAlice/venv/bin/python main.py')
		serviceFile.replace('#USER', f'User={getpass.getuser()}')

		Path('/tmp/service').write_text(serviceFile)
		subprocess.run(['sudo', 'mv', 'service', serviceFilePath])

		self.logInfo('Installing audio hardware')
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

			serviceFile = Path(f'/home/{getpass.getuser()}/hermesLedControl/hermesledcontrol.service').read_text()
			serviceFile.replace('%WORKING_DIR%', f'/home/{getpass.getuser()}/hermesLedControl')
			serviceFile.replace('%EXECSTART%', f'/home/{getpass.getuser()}/hermesLedControl/venv/bin/python main.py --hardware=%HARDWARE% --pattern=projectalice')
			serviceFile.replace('%USER%', f'{getpass.getuser()}')

			Path('/tmp/service').write_text(serviceFile)
			subprocess.run(['sudo', 'mv', 'service', serviceFilePath])


		if audioHardware in {'respeaker2', 'respeaker4', 'respeaker6MicArray'}:
			subprocess.run(['sudo', Path(self._rootDir, 'system/scripts/audioHardware/respeakers.sh')])
			if initConfs['useHLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', f's/%HARDWARE%/{audioHardware}/', str(hlcServiceFilePath)])

			if audioHardware == 'respeaker6MicArray':
				subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system', 'asounds', 'respeaker6micarray.conf'), Path(ASOUND)])

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

			snipsConf['snips-audio-server']['mike'] = 'MATRIXIO-SOUND: - (hw:2,0)'

			if initConfs['useHLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', f's/%HARDWARE%/{audioHardware.lower()}/', str(hlcServiceFilePath)])

		elif audioHardware == 'googleAIY':
			subprocess.run(['sudo', Path(self._rootDir, 'system/scripts/audioHardware/aiy.sh')])
			if initConfs['useHLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', 's/%HARDWARE%/googleAIY/', str(hlcServiceFilePath)])

		elif audioHardware == 'usbMic':
			subprocess.run(['sudo', Path(self._rootDir, 'system/scripts/audioHardware/usbmic.sh')])
			subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system', 'asounds', 'usbmic.conf'), Path(ASOUND)])

		elif audioHardware == 'ps3eye':
			subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system', 'asounds', 'ps3eye.conf'), Path(ASOUND)])
			asoundrc = f'/home/{getpass.getuser()}/.asoundrc'
			subprocess.run(['echo', 'pcm.dsp0 {', '>', asoundrc])
			subprocess.run(['echo', '    type plug', '>>', asoundrc])
			subprocess.run(['echo', '    slave.pcm "dmix"', '>>', asoundrc])
			subprocess.run(['echo', '}', '>>', asoundrc])

		elif audioHardware == 'jabra410':
			subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system', 'asounds', 'jabra410.conf'), Path(ASOUND)])

		subprocess.run(['sudo', 'systemctl', 'daemon-reload'])

		sort = dict(sorted(confs.items()))
		sort['skills'] = sort.pop('skills')

		try:
			confString = json.dumps(sort, indent=4).replace('false', 'False').replace('true', 'True')
			self._confsFile.write_text(f'settings = {confString}')
		except Exception as e:
			self.logFatal(f'An error occured while writting final configuration file: {e}')
		else:
			importlib.reload(config)

		snipsConf.dump()

		subprocess.run(['sudo', 'rm', '-rf', Path(self._rootDir, 'assistant')])

		if initConfs['keepYAMLBackup']:
			subprocess.run(['sudo', 'mv', Path(YAML), Path('/boot/ProjectAlice.yaml.bak')])
		else:
			subprocess.run(['sudo', 'rm', Path(YAML)])

		self.logWarning('Initializer done with configuring')
		time.sleep(2)
		subprocess.run(['sudo', 'systemctl', 'enable', 'ProjectAlice'])
		subprocess.run(['sudo', 'shutdown', '-r', 'now'])


	def loadSnipsConfigurations(self) -> TomlFile:
		self.logInfo('Loading Snips configuration file')
		snipsConfig = Path(SNIPS_TOML)

		if snipsConfig.exists():
			subprocess.run(['sudo', 'rm', SNIPS_TOML])

		subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system/snips/snips.toml'), Path(SNIPS_TOML)])

		return TomlFile.loadToml(snipsConfig)


	@staticmethod
	def getUpdateSource(definedSource: str) -> str:
		updateSource = 'master'
		if definedSource == 'master':
			return updateSource

		req = requests.get('https://api.github.com/repos/project-alice-assistant/ProjectAlice/branches')
		result = req.json()

		versions = list()
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


	@staticmethod
	def newConfs():
		return {configName: configData['values'] if 'dataType' in configData and configData['dataType'] == 'list' else configData['defaultValue'] if 'defaultValue' in configData else configData for configName, configData in configTemplate.settings.items()}
