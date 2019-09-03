import importlib
import json
import logging
import shutil
import subprocess
import time
from pathlib import Path

import yaml

from core.commons import commons


class Initializer:

	NAME = 'ProjectAlice'

	_WPA_FILE = '''country={wifiCountryCode}
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="{wifiNetworkName}"
    scan_ssid=1
    psk="{wifiWPAPass}"
    key_mgmt=WPA-PSK
}
	'''

	def __init__(self):
		self._logger = logging.getLogger('ProjectAlice')
		self._logger.info('Starting Project Alice initializer')

		confsFile = Path(commons.rootDir(), 'config.py')
		confsSample = Path(commons.rootDir(), 'configSample.py')

		initFile = Path('/boot/ProjectAlice.yaml')
		if not initFile.exists() and not confsFile.exists():
			self.fatal('Init file not found and there\'s no configuration file, aborting Project Alice start')
		elif not initFile.exists():
			return

		with initFile.open(mode='r') as f:
			try:
				initConfs = yaml.safe_load(f)
			except yaml.YAMLError as e:
				self.fatal('Failed loading init configurations: {}'.format(e))

		if not confsFile.exists() and not confsSample.exists():
			self.fatal('No config and no config sample found, can\'t continue')

		elif not confsFile.exists() and confsSample.exists():
			self.warning('No config file found, creating it from sample file')
			shutil.copyfile(src=Path(commons.rootDir(), 'configSample.py'), dst=Path(commons.rootDir(), 'config.py'))

		elif confsFile.exists() and not initConfs['forceRewrite']:
			self.warning('Config file already existing and user not wanting to rewrite, aborting')
			return

		elif confsFile.exists() and initConfs['forceRewrite']:
			self.warning('Config file found and force rewrite specified, let\'s restart all this!')
			Path(commons.rootDir(), 'config.py').unlink()
			shutil.copyfile(src=Path(commons.rootDir(), 'configSample.py'), dst=Path(commons.rootDir(), 'config.py'))


		config = importlib.import_module('config')
		confs = config.settings.copy()

		if not initConfs['wifiCountryCode'] or not initConfs['wifiNetworkName'] or not initConfs['wifiWPAPass']:
			self.fatal('You must specify the wifi parameters')

		# Let's connect to wifi!
		self._logger.info('Setting up wifi')
		wpaFile = self._WPA_FILE.format(**initConfs)

		file = Path(commons.rootDir(), 'wifi.conf')
		file.write_text(wpaFile)

		self._logger.info('wpa_supplicant.conf')
		subprocess.run(['sudo', 'mv', file, Path('/etc/wpa_supplicant/wpa_supplicant.conf')])

		self._logger.info('Turning off wifi')
		subprocess.run(['sudo', 'ifconfig', 'wlan0', 'down'])
		time.sleep(5)
		self._logger.info('Turning it back on')
		subprocess.run(['sudo', 'ifconfig', 'wlan0', 'up'])
		time.sleep(5)

		confs['ssid'] = initConfs['wifiNetworkName']
		confs['wifipassword'] = initConfs['wifiWPAPass']

		# Now let's dump some values to their respective places
		# First those that need some checks and self filling in case
		confs['mqttHost'] = initConfs['mqttHost'] or 'localhost'
		confs['mqttPort'] = initConfs['mqttPort'] or 1883

		if not initConfs['snipsConsoleLogin'] or not initConfs['snipsConsolePassword'] or not initConfs['intentsOwner']:
			self.fatal('You must specify a Snips console login, password and intent owner')

		confs['snipsConsoleLogin'] = initConfs['snipsConsoleLogin']
		confs['snipsConsolePassword'] = initConfs['snipsConsolePassword']
		confs['intentsOwner'] = initConfs['intentsOwner']

		confs['stayCompletlyOffline'] = initConfs['stayCompletlyOffline']
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
			confs['keepASROffline'] = initConfs['keepASROffline']
			confs['keepTTSOffline'] = initConfs['keepTTSOffline']
			confs['moduleAutoUpdate'] = initConfs['moduleAutoUpdate']
			confs['asr'] = initConfs['asr']
			confs['tts'] = initConfs['tts']
			confs['awsRegion'] = initConfs['awsRegion']
			confs['awsAccessKey'] = initConfs['awsAccessKey']
			confs['awsSecretKey'] = initConfs['awsSecretKey']

			if initConfs['googleServiceFile']:
				googleCreds = Path(commons.rootDir(), 'credentials/googlecredentials.json')
				googleCreds.write_text(json.dumps(initConfs['googleServiceFile']))


		# Those that don't need checking
		confs['micSampleRate'] = initConfs['micSampleRate']
		confs['micChannels'] = initConfs['micChannels']
		confs['useSLC'] = initConfs['useSLC']
		confs['webInterfaceActive'] = initConfs['webInterfaceActive']
		confs['newDeviceBroadcastPort'] = initConfs['newDeviceBroadcastPort']
		confs['activeLanguage'] = initConfs['activeLanguage']
		confs['activeCountryCode'] = initConfs['activeCountryCode']
		confs['baseCurrency'] = initConfs['baseCurrency']
		confs['baseUnits'] = initConfs['baseUnits']
		confs['enableDataStoring'] = initConfs['enableDataStoring']
		confs['autoPruneStoredData'] = initConfs['autoPruneStoredData']
		confs['probabilityTreshold'] = initConfs['probabilityTreshold']
		confs['shortReplies'] = initConfs['shortReplies']
		confs['whisperWhenSleeping'] = initConfs['whisperWhenSleeping']
		confs['ttsType'] = initConfs['ttsType']
		confs['ttsVoice'] = initConfs['ttsVoice']

		self._logger.info('Installing audio hardware')
		audioHardware = ''
		for hardware in initConfs['audioHardware']:
			if initConfs['audioHardware'][hardware]:
				audioHardware = hardware
				break

		if audioHardware in ('respeaker2', 'respeaker4'):
			subprocess.call(['sudo', Path(commons.rootDir(), 'system/scripts/audioHardware/respeakers.sh')])
			subprocess.run(['sudo', 'sed', '-i', '-e', 's/%HARDWARE%/{}/'.format(audioHardware), Path('/etc/systemd/system/snipsledcontrol.service')])
		elif audioHardware == 'respeaker7':
			subprocess.call(['sudo', Path(commons.rootDir(), 'system/scripts/audioHardware/respeaker7.sh')])
			subprocess.run(['sudo', 'sed', '-i', '-e', 's/%HARDWARE%/respeaker7MicArray/', Path('/etc/systemd/system/snipsledcontrol.service')])
		elif audioHardware == 'respeakerCoreV2':
			subprocess.call(['sudo', Path(commons.rootDir(), 'system/scripts/audioHardware/respeakerCoreV2.sh')])
			subprocess.run(['sudo', 'sed', '-i', '-e', 's/%HARDWARE%/{}/'.format(audioHardware), Path('/etc/systemd/system/snipsledcontrol.service')])
		elif audioHardware in ('matrixCreator', 'matrixVoice'):
			subprocess.call(['sudo', Path(commons.rootDir(), 'system/scripts/audioHardware/matrix.sh')])
			subprocess.run(['sudo', 'sed', '-i', '-e', 's/%HARDWARE%/{}/'.format(audioHardware.lower()), Path('/etc/systemd/system/snipsledcontrol.service')])

		subprocess.run(['sudo', 'systemctl', 'daemon-reload'])

		sort = dict(sorted(confs.items()))
		# pop modules key so it gets added in the back
		sort['modules'] = sort.pop('modules')

		try:
			s = json.dumps(sort, indent=4).replace('false', 'False').replace('true', 'True')
			Path('config.py').write_text('settings = {}'.format(s))

		except Exception as e:
			self.fatal('An error occured while writting final configuration file: {}'.format(e))
		else:
			importlib.reload(config)


		self.warning('Initializer done with configuring')
		Path('/boot/ProjectAlice.yaml').unlink()


	def fatal(self, text: str):
		self._logger.fatal(text)
		exit()


	def warning(self, text: str):
		self._logger.warning(text)
