# -*- coding: utf-8 -*-
import getpass
import json
import logging
import subprocess
from pathlib import Path

import importlib
import os
import re
import shutil
import yaml

from core.commons import commons


class Initializer:

	NAME = 'ProjectAlice'

	def __init__(self):
		self._logger = logging.getLogger('ProjectAlice')
		self._logger.info('Starting Project Alice initializer')

		confsFile = Path(os.path.join(commons.rootDir(), 'config.py'))
		confsSample = Path(os.path.join(commons.rootDir(), 'configSample.py'))

		initFile = Path(os.path.join('/boot', 'ProjectAlice.yaml'))
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
			shutil.copyfile(src=os.path.join(commons.rootDir(), 'configSample.py'), dst=os.path.join(commons.rootDir(), 'config.py'))

		elif confsFile.exists() and not initConfs['forceRewrite']:
			self.warning('Config file already existing and user not wanting to rewrite, aborting')
			return

		elif confsFile.exists() and initConfs['forceRewrite']:
			self.warning('Config file found and force rewrite specified, let\'s restart all this!')
			os.remove(os.path.join(commons.rootDir(), 'config.py'))
			shutil.copyfile(src=os.path.join(commons.rootDir(), 'configSample.py'), dst=os.path.join(commons.rootDir(), 'config.py'))


		config = importlib.import_module('config')
		confs = config.settings.copy()

		# Let's get the ssid and pass automagically from wpa_supplicant file. For that we need to copy it to Project Alice, because we don't want to change its default permissions
		# and then delete it
		wpaSupCopy = Path(os.path.join(commons.rootDir(), 'wpa_supplicant.conf'))
		ret = subprocess.run(['sudo', 'cp', os.path.join('/etc', 'wpa_supplicant', 'wpa_supplicant.conf'), wpaSupCopy], stdout=subprocess.PIPE)
		if ret.returncode > 0:
			self.fatal('wpa_supplicant.conf not found, are we connected to wlan??')

		ret = subprocess.run(['sudo', 'chown', getpass.getuser(), wpaSupCopy], stdout=subprocess.PIPE)

		file = Path(os.path.join(commons.rootDir(), 'wpa_supplicant.conf'))
		if not file.exists():
			self.fatal('wpa_supplicant.conf not found, are we connected to wlan??')

		ssid = ''
		pwd = ''
		with file.open(mode='r') as f:
			for line in f:
				ssidRegex = re.search('.*ssid="(.*?)"', line)
				if not ssid and ssidRegex and ssidRegex.group(1):
					ssid = ssidRegex.group(1)
					continue

				pwdRegex = re.search('.*psk="(.*?)"', line)
				if not pwd and pwdRegex and pwdRegex.group(1):
					pwd = pwdRegex.group(1)
					continue

				if pwd and ssid:
					break

		os.remove(os.path.join(commons.rootDir(), 'wpa_supplicant.conf'))

		if not ssid or not pwd:
			self.fatal('Wlan config not found, are we connected to wlan?')

		confs['ssid'] = ssid
		confs['wifipassword'] = pwd

		# Now let's dump some values to their respective places
		# First those that need some checks and self filling in case
		confs['mqttHost'] = initConfs['mqttHost'] if initConfs['mqttHost'] else 'localhost'
		confs['mqttPort'] = initConfs['mqttPort'] if initConfs['mqttPort'] else 1883

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
				googleCreds = Path(os.path.join(commons.rootDir(), 'credentials', 'googlecredentials.json'))
				if googleCreds.exists():
					os.remove(googleCreds)

				with googleCreds.open(mode='w') as f:
					json.dump(initConfs['googleServiceFile'], f)


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


		# Do some sorting, just for the eyes
		temp = sorted(list(confs.keys()))
		sort = dict()
		modules = dict()
		for key in temp:
			if key == 'modules':
				modules = confs[key]
				continue

			sort[key] = confs[key]

		sort['modules'] = modules

		try:
			s = json.dumps(sort, indent = 4).replace('false', 'False').replace('true', 'True')
			with open('config.py', 'w') as f:
				f.write('settings = {}'.format(s))
		except Exception as e:
			self.fatal('An error occured while writting final configuration file: {}'.format(e))
		else:
			importlib.reload(config)


		self.warning('Initializer done with configuring')
		# TODO Active before public version!
		#os.remove(os.path.join('/boot/ProjectAlice.yaml'))


	def fatal(self, text: str):
		self._logger.fatal(text)
		exit()


	def warning(self, text: str):
		self._logger.warning(text)

