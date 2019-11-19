import getpass
import importlib
import json
import socket
import subprocess
import time
from pathlib import Path

import requests

from core.base.model.TomlFile import TomlFile
from core.base.model.Version import Version

try:
	import yaml
except:
	subprocess.run(['./venv/bin/pip3', 'install', 'pyyaml'])
	import yaml

import configTemplate
from core.base.model.ProjectAliceObject import ProjectAliceObject


class initDict(dict):

	def __init__(self, default: dict):
		super().__init__(default)


	def __getitem__(self, item):
		try:
			return super().__getitem__(item) or ''
		except:
			print(f'[Initializer] Missing key "{item}" in provided yaml file. Are you using a deprecated yaml file version?')
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
		super().__init__(logDepth=3)
		self.logInfo('Starting Project Alice initializer')

		self._rootDir = Path(__file__).resolve().parent.parent

		self._confsFile = Path(self._rootDir, 'config.py')
		self._confsSample = Path(self._rootDir, 'configTemplate.py')
		self._initFile = Path('/boot/ProjectAlice.yaml')
		self._latest = 1.10


	def initProjectAlice(self) -> bool:
		if not self._initFile.exists() and not self._confsFile.exists():
			self.fatal('Init file not found and there\'s no configuration file, aborting Project Alice start')
		elif not self._initFile.exists():
			self.logInfo('No initialization needed')
			return False

		with self._initFile.open(mode='r') as f:
			try:
				load = yaml.safe_load(f)
				if not load:
					raise  yaml.YAMLError

				initConfs = initDict(load)
			except yaml.YAMLError as e:
				self.fatal(f'Failed loading init configurations: {e}')

		# Check that we are running using the latest yaml
		if float(initConfs['version']) < self._latest:
			self.fatal('The yaml file you are using is deprecated. Please update it before trying again')

		wpaSupplicant = Path('/etc/wpa_supplicant/wpa_supplicant.conf')
		if not wpaSupplicant.exists() and initConfs['useWifi']:
			self.logInfo('Setting up wifi')

			if not initConfs['wifiCountryCode'] or not initConfs['wifiNetworkName'] or not initConfs['wifiWPAPass']:
				self.fatal('You must specify the wifi parameters')

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
			subprocess.run(['/usr/bin/sudo', '/sbin/shutdown', '-r', 'now'])
			exit(0)

		try:
			socket.create_connection(('www.google.com', 80))
			connected = True
		except:
			connected = False

		if not connected:
			self.fatal('Your device needs internet access to continue, to download the updates and create the assistant')

		if not initConfs['snipsConsoleLogin'] or not initConfs['snipsConsolePassword'] or not initConfs['intentsOwner']:
			self.fatal('You must specify a Snips console login, password and intent owner')

		# Update our system and sources
		subprocess.run(['sudo', 'apt-get', 'update'])
		subprocess.run(['sudo', 'apt-get', 'dist-upgrade', '-y'])
		subprocess.run(['git', 'clean', '-df'])
		subprocess.run(['git', 'stash'])
		subprocess.run(['git', 'checkout', self.getUpdateSource(initConfs['updateChannel'])])
		subprocess.run(['git', 'pull'])
		subprocess.run(['git', 'stash', 'clear'])

		time.sleep(1)

		subprocess.run(['./venv/bin/pip3', 'uninstall', '-y', '-r', str(Path(self._rootDir, 'pipuninstalls.txt'))])

		if not self._confsFile.exists() and not self._confsSample.exists():
			self.fatal('No config and no config template found, can\'t continue')

		elif not self._confsFile.exists() and self._confsSample.exists():
			self.warning('No config file found, creating it from sample file')
			confs = self.newConfs()
			Path('config.py').write_text(f"settings = {json.dumps(confs, indent=4).replace('false', 'False').replace('true', 'True')}")

		elif self._confsFile.exists() and not initConfs['forceRewrite']:
			self.warning('Config file already existing and user not wanting to rewrite, aborting')
			return False

		elif self._confsFile.exists() and initConfs['forceRewrite']:
			self.warning('Config file found and force rewrite specified, let\'s restart all this!')
			Path(self._rootDir, 'config.py').unlink()
			confs = self.newConfs()
			Path('config.py').write_text(f"settings = {json.dumps(confs, indent=4).replace('false', 'False').replace('true', 'True')}")

		config = importlib.import_module('config')
		confs = config.settings.copy()

		# Do some installation if wanted by the user
		if initConfs['doGroundInstall']:
			subprocess.run(['./venv/bin/pip3', 'install', '-r', str(Path(self._rootDir, 'piprequirements.txt'))])

			subprocess.run(['sudo', 'bash', '-c', 'echo "deb https://raspbian.snips.ai/$(lsb_release -cs) stable main" > /etc/apt/sources.list.d/snips.list'])
			subprocess.run(['sudo', 'apt-key', 'adv', '--keyserver', 'gpg.mozilla.org', '--recv-keys', 'D4F50CDCA10A2849'])
			subprocess.run(['sudo', 'apt-get', 'update'])

			reqs = [line.rstrip('\n') for line in open(Path(self._rootDir, 'sysrequirements.txt'))]
			subprocess.run(['sudo', 'apt-get', 'install', '-y', '--allow-unauthenticated'] + reqs)

			subprocess.run(['sudo', 'systemctl', 'stop', 'snips-*'])
			subprocess.run(['sudo', 'systemctl', 'disable', 'snips-asr'])
			subprocess.run(['sudo', 'systemctl', 'disable', 'snips-nlu'])
			subprocess.run(['sudo', 'systemctl', 'disable', 'snips-dialogue'])
			subprocess.run(['sudo', 'systemctl', 'disable', 'snips-injection'])
			subprocess.run(['sudo', 'systemctl', 'disable', 'snips-hotword'])
			subprocess.run(['sudo', 'systemctl', 'disable', 'snips-audio-server'])
			subprocess.run(['sudo', 'systemctl', 'disable', 'snips-tts'])

		# Now let's dump some values to their respective places
		# First those that need some checks and self filling in case unspecified
		confs['mqttHost'] = str(initConfs['mqttHost']) or 'localhost'
		confs['mqttPort'] = initConfs['mqttPort'] or 1883

		confs['snipsConsoleLogin'] = initConfs['snipsConsoleLogin']
		confs['snipsConsolePassword'] = initConfs['snipsConsolePassword']
		confs['intentsOwner'] = initConfs['intentsOwner']

		confs['stayCompletlyOffline'] = bool(initConfs['stayCompletlyOffline'])
		if initConfs['stayCompletlyOffline']:
			confs['keepASROffline'] = True
			confs['keepTTSOffline'] = True
			confs['moduleAutoUpdate'] = False
			confs['asr'] = 'snips'
			confs['tts'] = 'pico'
			confs['awsRegion'] = ''
			confs['awsAccessKey'] = ''
			confs['awsSecretKey'] = ''
		else:
			confs['keepASROffline'] = bool(initConfs['keepASROffline'])
			confs['keepTTSOffline'] = bool(initConfs['keepTTSOffline'])
			confs['moduleAutoUpdate'] = bool(initConfs['moduleAutoUpdate'])
			confs['asr'] = initConfs['asr'] if initConfs['asr'] in ('snips', 'google') else 'snips'
			confs['tts'] = initConfs['tts'] if initConfs['tts'] in ('pico', 'snips', 'mycroft', 'amazon', 'google') else 'pico'
			confs['awsRegion'] = initConfs['awsRegion']
			confs['awsAccessKey'] = initConfs['awsAccessKey']
			confs['awsSecretKey'] = initConfs['awsSecretKey']

			if initConfs['googleServiceFile']:
				googleCreds = Path(self._rootDir, 'credentials/googlecredentials.json')
				googleCreds.write_text(json.dumps(initConfs['googleServiceFile']))

		# Those that don't need checking
		confs['ssid'] = initConfs['wifiNetworkName'] or ''
		confs['wifipassword'] = str(initConfs['wifiWPAPass']) or ''
		confs['micSampleRate'] = int(initConfs['micSampleRate']) or 16000
		confs['micChannels'] = int(initConfs['micChannels']) or 1
		confs['useSLC'] = bool(initConfs['useSLC'])
		confs['webInterfaceActive'] = bool(initConfs['webInterfaceActive'])
		confs['devMode'] = bool(initConfs['devMode'])
		confs['newDeviceBroadcastPort'] = int(initConfs['newDeviceBroadcastPort']) or 12354
		confs['activeLanguage'] = initConfs['activeLanguage'] if initConfs['activeLanguage'] in ('en', 'de', 'fr') else 'en'
		confs['activeCountryCode'] = initConfs['activeCountryCode'] or 'US'
		confs['baseCurrency'] = initConfs['baseCurrency'] or 'USD'
		confs['baseUnits'] = initConfs['baseUnits'] if initConfs['baseUnits'] in ('metric', 'kelvin', 'imperial') else 'metric'
		confs['enableDataStoring'] = bool(initConfs['enableDataStoring'])
		confs['autoPruneStoredData'] = initConfs['autoPruneStoredData'] or 1000
		confs['probabilityThreshold'] = float(initConfs['probabilityThreshold']) or 0.5
		confs['shortReplies'] = bool(initConfs['shortReplies'])
		confs['whisperWhenSleeping'] = bool(initConfs['whisperWhenSleeping'])
		confs['ttsLanguage'] = initConfs['ttsLanguage'] or confs['activeLanguage']
		confs['ttsType'] = initConfs['ttsType'] if initConfs['ttsType'] in ('female', 'male') else 'female'
		confs['ttsVoice'] = initConfs['ttsVoice'] or ''
		confs['githubUsername'] = initConfs['githubUsername'] or ''
		confs['githubToken'] = initConfs['githubToken'] or ''
		confs['ttsLanguage'] = initConfs['ttsLanguage'] or ''
		confs['updateChannel'] = initConfs['updateChannel'] if initConfs['updateChannel'] in ('master', 'rc', 'beta', 'alpha') else 'master'
		confs['mqtt_username'] = str(initConfs['mqttUser']) or ''
		confs['mqttPassword'] = str(initConfs['mqttPassword']) or ''
		confs['mqttTLSFile'] = initConfs['mqttTLSFile'] or ''

		if initConfs['snipsProjectId'] and confs['activeLanguage'] in confs['supportedLanguages']:
			confs['supportedLanguages'][confs['activeLanguage']]['snipsProjectId'] = initConfs['snipsProjectId']

		snipsConf = self.loadSnipsConfigurations()
		if not snipsConf:
			self.fatal('Error loading snips.toml')

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
		if not serviceFilePath.exists():
			subprocess.run(['sudo', 'cp', 'ProjectAlice.service', serviceFilePath])

		subprocess.run(['sudo', 'sed', '-i', '-e', f's/\#WORKINGDIR/WorkingDirectory=\/home\/{getpass.getuser()}\/ProjectAlice/', str(serviceFilePath)])
		subprocess.run(['sudo', 'sed', '-i', '-e', f's/\#EXECSTART/ExecStart=\/home\/{getpass.getuser()}\/ProjectAlice\/venv\/bin\/python3 main.py/', str(serviceFilePath)])
		subprocess.run(['sudo', 'sed', '-i', '-e', f's/\#USER/User={getpass.getuser()}/', str(serviceFilePath)])

		self.logInfo('Installing audio hardware')
		audioHardware = ''
		for hardware in initConfs['audioHardware']:
			if initConfs['audioHardware'][hardware]:
				audioHardware = hardware
				break

		slcServiceFilePath = Path('/etc/systemd/system/snipsledcontrol.service')
		if initConfs['useSLC']:

			if not Path('/home', getpass.getuser(), 'snipsLedControl'):
				subprocess.run(['git', 'clone', 'https://github.com/Psychokiller1888/snipsLedControl.git', str(Path('/home', getpass.getuser(), 'snipsLedControl'))])
			else:
				subprocess.run(['git', '-C', str(Path('/home', getpass.getuser(), 'snipsLedControl')), 'stash'])
				subprocess.run(['git', '-C', str(Path('/home', getpass.getuser(), 'snipsLedControl')), 'pull'])
				subprocess.run(['git', '-C', str(Path('/home', getpass.getuser(), 'snipsLedControl')), 'stash', 'clear'])

			if not slcServiceFilePath.exists():
				subprocess.run(['sudo', 'cp', f'/home/{getpass.getuser()}/snipsLedControl/snipsledcontrol.service', str(slcServiceFilePath)])

			subprocess.run(['sudo', 'sed', '-i', '-e', f's/%WORKING_DIR%/\/home\/{getpass.getuser()}\/snipsLedControl/', str(slcServiceFilePath)])
			subprocess.run(['sudo', 'sed', '-i', '-e', f's/%EXECSTART%/\/home\/{getpass.getuser()}\/snipsLedControl\/venv\/bin\/python3 main.py --hardware=%HARDWARE% --pattern=projectalice/', str(slcServiceFilePath)])
			subprocess.run(['sudo', 'sed', '-i', '-e', f's/%USER%/{getpass.getuser()}/', str(slcServiceFilePath)])

		if audioHardware in {'respeaker2', 'respeaker4', 'respeaker6MicArray'}:
			subprocess.run(['sudo', Path(self._rootDir, 'system/scripts/audioHardware/respeakers.sh')])
			if initConfs['useSLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', f's/%HARDWARE%/{audioHardware}/', str(slcServiceFilePath)])

			if audioHardware == 'respeaker6MicArray':
				subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system', 'asounds', 'respeaker6micarray.conf'), Path('/etc/asound.conf')])

		elif audioHardware == 'respeaker7':
			subprocess.run(['sudo', Path(self._rootDir, 'system/scripts/audioHardware/respeaker7.sh')])
			if initConfs['useSLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', 's/%HARDWARE%/respeaker7MicArray/', str(slcServiceFilePath)])

		elif audioHardware == 'respeakerCoreV2':
			subprocess.run(['sudo', Path(self._rootDir, 'system/scripts/audioHardware/respeakerCoreV2.sh')])
			if initConfs['useSLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', f's/%HARDWARE%/{audioHardware}/', str(slcServiceFilePath)])

		elif audioHardware in {'matrixCreator', 'matrixVoice'}:
			subprocess.run(['sudo', Path(self._rootDir, 'system/scripts/audioHardware/matrix.sh')])
			subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system', 'asounds', 'matrix.conf'), Path('/etc/asound.conf')])

			snipsConf['snips-audio-server']['mike'] = 'MATRIXIO-SOUND: - (hw:2,0)'

			if initConfs['useSLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', f's/%HARDWARE%/{audioHardware.lower()}/', str(slcServiceFilePath)])

		elif audioHardware == 'googleAIY':
			subprocess.run(['sudo', Path(self._rootDir, 'system/scripts/audioHardware/aiy.sh')])
			if initConfs['useSLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', 's/%HARDWARE%/googleAIY/', str(slcServiceFilePath)])

		elif audioHardware == 'usbMic':
			subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system', 'asounds', 'usbmic.conf'), Path('/etc/asound.conf')])

		subprocess.run(['sudo', 'systemctl', 'daemon-reload'])

		sort = dict(sorted(confs.items()))
		sort['modules'] = sort.pop('modules')

		try:
			s = json.dumps(sort, indent=4).replace('false', 'False').replace('true', 'True')
			self._confsFile.write_text(f'settings = {s}')
		except Exception as e:
			self.fatal(f'An error occured while writting final configuration file: {e}')
		else:
			importlib.reload(config)

		snipsConf.dump()

		subprocess.run(['sudo', 'rm', '-rf', Path(self._rootDir, 'assistant')])
		subprocess.run(['sudo', 'rm', '-rf', Path(self._rootDir, 'trained', 'assistants', f"assistant_{confs['activeLanguage']}")])
		subprocess.run(['sudo', 'rm', '-rf', Path(self._rootDir, 'var', 'assistants', confs['activeLanguage'])])

		if initConfs['keepYAMLBackup']:
			subprocess.run(['sudo', 'mv', Path('/boot/ProjectAlice.yaml'), Path('/boot/ProjectAlice.yaml.bak')])
		else:
			subprocess.run(['sudo', 'rm', Path('/boot/ProjectAlice.yaml')])

		self.warning('Initializer done with configuring')
		time.sleep(2)
		subprocess.run(['sudo', 'systemctl', 'enable', 'ProjectAlice'])
		subprocess.run(['sudo', 'shutdown', '-r', 'now'])


	def fatal(self, text: str):
		self.logFatal(text)
		exit()


	def warning(self, text: str):
		self.logWarning(text)


	def loadSnipsConfigurations(self) -> TomlFile:
		self.logInfo('Loading Snips configuration file')
		snipsConfig = Path('/etc/snips.toml')

		if not snipsConfig.exists():
			subprocess.run(['sudo', 'cp', Path(self._rootDir, 'system/snips/snips.toml'), Path('/etc/snips.toml')])

		return TomlFile.loadToml(snipsConfig)


	@staticmethod
	def getUpdateSource(definedSource: str) -> str:
		updateSource = 'master'
		if definedSource == 'master':
			return updateSource

		req = requests.get('https://api.github.com/repos/project-alice-powered-by-snips/ProjectAlice/branches')
		result = req.json()
		if result:
			userUpdatePref = definedSource
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


	@staticmethod
	def newConfs():
		return {configName: configData['defaultValue'] if 'defaultValue' in configData else configData['values'] if 'dataType' in configData and 'dataType' == 'list' else configData for configName, configData in configTemplate.settings.items()}
