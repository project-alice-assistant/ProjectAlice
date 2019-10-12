import getpass
import importlib
import json
import shutil
import subprocess
import time
from pathlib import Path

import yaml

from core.commons import commons
from core.util.model.Logger import Logger


class initDict(dict, Logger):

	def __init__(self, default: dict):
		super().__init__(default)


	def __getitem__(self, item):
		try:
			return super().__getitem__(item) or ''
		except:
			self.logWarning(f'Missing key "{item}" in provided yaml file. Are you using a deprecated yaml file version?')
			return ''


class Initializer(Logger):

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
		self.logInfo('Starting Project Alice initializer')

		self._confsFile = Path(commons.rootDir(), 'config.py')
		self._confsSample = Path(commons.rootDir(), 'configSample.py')
		self._initFile = Path('/boot/ProjectAlice.yaml')
		self._latest = 1.03


	def initProjectAlice(self) -> bool:
		if not self._initFile.exists() and not self._confsFile.exists():
			self.fatal('Init file not found and there\'s no configuration file, aborting Project Alice start')
		elif not self._initFile.exists():
			return False

		with self._initFile.open(mode='r') as f:
			try:
				initConfs = initDict(yaml.safe_load(f))
			except yaml.YAMLError as e:
				self.fatal(f'Failed loading init configurations: {e}')

		# Check that we are running using the latest yaml
		if float(initConfs['version']) < self._latest:
			self.fatal('The yaml file you are using is deprecated. Please update it before trying again')

		# Let's connect to wifi!
		if not initConfs['wifiCountryCode'] or not initConfs['wifiNetworkName'] or not initConfs['wifiWPAPass']:
			self.fatal('You must specify the wifi parameters')

		wpaSupplicant = Path('/etc/wpa_supplicant/wpa_supplicant.conf')
		bootWpaSupplicant = Path('/boot/wpa_supplicant.conf')

		if not wpaSupplicant.exists():
			self.logInfo('Setting up wifi')
			wpaFile = self._WPA_FILE\
				.replace('%wifiCountryCode%', initConfs['wifiCountryCode'])\
				.replace('%wifiNetworkName%', initConfs['wifiNetworkName'])\
				.replace('%wifiWPAPass%', initConfs['wifiWPAPass'])

			file = Path(commons.rootDir(), 'wifi.conf')
			file.write_text(wpaFile)

			self.logInfo('wpa_supplicant.conf')
			subprocess.run(['sudo', 'mv', str(file), bootWpaSupplicant])
			time.sleep(1)
			subprocess.run(['/usr/bin/sudo', '/sbin/shutdown', '-r', 'now'])
			exit(0)

		if not initConfs['snipsConsoleLogin'] or not initConfs['snipsConsolePassword'] or not initConfs['intentsOwner']:
			self.fatal('You must specify a Snips console login, password and intent owner')

		if not self._confsFile.exists() and not self._confsSample.exists():
			self.fatal('No config and no config sample found, can\'t continue')

		elif not self._confsFile.exists() and self._confsSample.exists():
			self.warning('No config file found, creating it from sample file')
			shutil.copyfile(src=Path(commons.rootDir(), 'configSample.py'), dst=Path(commons.rootDir(), 'config.py'))

		elif self._confsFile.exists() and not initConfs['forceRewrite']:
			self.warning('Config file already existing and user not wanting to rewrite, aborting')
			return False

		elif self._confsFile.exists() and initConfs['forceRewrite']:
			self.warning('Config file found and force rewrite specified, let\'s restart all this!')
			Path(commons.rootDir(), 'config.py').unlink()
			shutil.copyfile(src=Path(commons.rootDir(), 'configSample.py'), dst=Path(commons.rootDir(), 'config.py'))

		config = importlib.import_module('config')
		confs = config.settings.copy()

		# Update our system and sources
		subprocess.run(['sudo', 'apt-get', 'update'])
		subprocess.run(['sudo', 'apt-get', 'dist-upgrade', '-y'])
		subprocess.run(['git', 'stash'])
		subprocess.run(['git', 'checkout', initConfs['updateChannel']])
		subprocess.run(['git', 'pull'])
		subprocess.run(['git', 'stash', 'clear'])


		# Do some installation if wanted by the user
		if initConfs['doGroundInstall']:
			subprocess.run(['sudo', 'bash', '-c', 'echo "deb https://raspbian.snips.ai/$(lsb_release -cs) stable main" > /etc/apt/sources.list.d/snips.list'])
			subprocess.run(['sudo', 'apt-key',  'adv', '--keyserver', 'gpg.mozilla.org', '--recv-keys', 'D4F50CDCA10A2849'])
			subprocess.run(['sudo', 'apt-get', 'update'])

			reqs = [line.rstrip('\n') for line in open(Path(commons.rootDir(), 'sysrequirements.txt'))]
			subprocess.run(['sudo', 'apt-get', 'install', '-y', '--allow-unauthenticated'] + reqs)
			subprocess.run(['./venv/bin/pip3', 'install', '-r', str(Path(commons.rootDir(), 'piprequirements.txt'))])
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
		confs['mqttPort'] = str(initConfs['mqttPort']) or '1883'

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
			confs['asr'] = initConfs['asr']
			confs['tts'] = initConfs['tts']
			confs['awsRegion'] = initConfs['awsRegion']
			confs['awsAccessKey'] = initConfs['awsAccessKey']
			confs['awsSecretKey'] = initConfs['awsSecretKey']

			if initConfs['googleServiceFile']:
				googleCreds = Path(commons.rootDir(), 'credentials/googlecredentials.json')
				googleCreds.write_text(json.dumps(initConfs['googleServiceFile']))

		# Those that don't need checking
		confs['ssid'] = initConfs['wifiNetworkName']
		confs['wifipassword'] = initConfs['wifiWPAPass']
		confs['micSampleRate'] = int(initConfs['micSampleRate'])
		confs['micChannels'] = int(initConfs['micChannels'])
		confs['useSLC'] = bool(initConfs['useSLC'])
		confs['webInterfaceActive'] = bool(initConfs['webInterfaceActive'])
		confs['newDeviceBroadcastPort'] = int(initConfs['newDeviceBroadcastPort'])
		confs['activeLanguage'] = initConfs['activeLanguage']
		confs['activeCountryCode'] = initConfs['activeCountryCode']
		confs['baseCurrency'] = initConfs['baseCurrency']
		confs['baseUnits'] = initConfs['baseUnits']
		confs['enableDataStoring'] = bool(initConfs['enableDataStoring'])
		confs['autoPruneStoredData'] = initConfs['autoPruneStoredData']
		confs['probabilityTreshold'] = float(initConfs['probabilityTreshold'])
		confs['shortReplies'] = bool(initConfs['shortReplies'])
		confs['whisperWhenSleeping'] = bool(initConfs['whisperWhenSleeping'])
		confs['ttsLanguage'] = initConfs['ttsLanguage']
		confs['ttsType'] = initConfs['ttsType']
		confs['ttsVoice'] = initConfs['ttsVoice']
		confs['githubUsername'] = initConfs['githubUsername']
		confs['githubToken'] = initConfs['githubToken']
		confs['ttsLanguage'] = initConfs['ttsLanguage']

		if initConfs['snipsProjectId'] and confs['activeLanguage'] in confs['supportedLanguages']:
			confs['supportedLanguages'][confs['activeLanguage']]['snipsProjectId'] = initConfs['snipsProjectId']

		if initConfs['deviceName'] != 'default':
			subprocess.run(['sudo', 'sed', '-i', '-e', f's/\# bind = "default@mqtt"/bind = "{initConfs["deviceName"]}@mqtt"/', Path('/etc/snips.toml')])
			subprocess.run(['sudo', 'sed', '-i', '-e', f's/bind = ".*@mqtt"/bind = "{initConfs["deviceName"]}@mqtt"/', Path('/etc/snips.toml')])
			subprocess.run(['sudo', 'sed', '-i', '-e', f's/DEFAULT_SITE_ID = \'default\'/DEFAULT_SITE_ID = \'{initConfs["deviceName"]}\'/', Path(commons.rootDir(), 'core/commons/constants.py')])

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
			subprocess.run(['sudo', Path(commons.rootDir(), 'system/scripts/audioHardware/respeakers.sh')])
			if initConfs['useSLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', f's/%HARDWARE%/{audioHardware}/', str(slcServiceFilePath)])

			if audioHardware == 'respeaker6MicArray':
				subprocess.run(['sudo', 'cp', Path(commons.rootDir(), 'system', 'asounds', 'respeaker6micarray.conf'), Path('/etc/asound.conf')])

		elif audioHardware == 'respeaker7':
			subprocess.run(['sudo', Path(commons.rootDir(), 'system/scripts/audioHardware/respeaker7.sh')])
			if initConfs['useSLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', 's/%HARDWARE%/respeaker7MicArray/', str(slcServiceFilePath)])

		elif audioHardware == 'respeakerCoreV2':
			subprocess.run(['sudo', Path(commons.rootDir(), 'system/scripts/audioHardware/respeakerCoreV2.sh')])
			if initConfs['useSLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', f's/%HARDWARE%/{audioHardware}/', str(slcServiceFilePath)])

		elif audioHardware in {'matrixCreator', 'matrixVoice'}:
			subprocess.run(['sudo', Path(commons.rootDir(), 'system/scripts/audioHardware/matrix.sh')])
			if initConfs['useSLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', f's/%HARDWARE%/{audioHardware.lower()}/', str(slcServiceFilePath)])

		elif audioHardware == 'googleAIY':
			subprocess.run(['sudo', Path(commons.rootDir(), 'system/scripts/audioHardware/aiy.sh')])
			if initConfs['useSLC']:
				subprocess.run(['sudo', 'sed', '-i', '-e', 's/%HARDWARE%/googleAIY/', str(slcServiceFilePath)])

		elif audioHardware == 'usbMic':
			subprocess.run(['sudo', 'cp', Path(commons.rootDir(), 'system', 'asounds', 'usbmic.conf'), Path('/etc/asound.conf')])

		subprocess.run(['sudo', 'systemctl', 'daemon-reload'])

		sort = dict(sorted(confs.items()))
		# pop modules key so it gets added in the back
		sort['modules'] = sort.pop('modules')

		try:
			s = json.dumps(sort, indent=4).replace('false', 'False').replace('true', 'True')
			self._confsFile.write_text(f'settings = {s}')
		except Exception as e:
			self.fatal(f'An error occured while writting final configuration file: {e}')
		else:
			importlib.reload(config)

		subprocess.run(['sudo', 'rm', '-rf', Path(commons.rootDir(), 'assistant')])
		subprocess.run(['sudo', 'rm', '-rf', Path(commons.rootDir(), 'trained', 'assistants', f"assistant_{confs['activeLanguage']}")])
		subprocess.run(['sudo', 'rm', '-rf', Path(commons.rootDir(), 'var', 'assistants', confs['activeLanguage'])])
		subprocess.run(['sudo', 'mv', str(Path('/boot/ProjectAlice.yaml')), str(Path('/boot/ProjectAlice.yaml.bak'))])

		self.warning('Initializer done with configuring')
		time.sleep(2)
		subprocess.run(['sudo', 'systemctl', 'enable', 'ProjectAlice'])
		subprocess.run(['sudo', 'shutdown', '-r', 'now'])


	def fatal(self, text: str):
		self.logFatal(text)
		exit()


	def warning(self, text: str):
		self.logWarning(text)
