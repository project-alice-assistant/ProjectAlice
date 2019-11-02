settings = {
	'notUnderstoodRetries': {
		'value': 3,
		'type': 'integer'
	},
	'ssid': {
		'value': '',
		'type': 'string'
	},
	'wifipassword': {
		'value': '',
		'type': 'string'
	},
	'mqttHost': {
		'value': 'localhost',
		'type': 'string'
	},
	'mqttPort': {
		'value': 1883,
		'type': 'integer'
	},
	'micSampleRate': {
		'value': 44100,
		'type': 'integer'
	},
	'micChannels': {
		'value': 1,
		'type': 'integer'
	},
	'enableDataStoring': {
		'value': False,
		'type': 'boolean'
	},
	'autoPruneStoredData': {
		'value': 0,
		'type': 'integer',
		'comment': 'Set to max entries to keep, 0 to disable pruning'
	},
	'probabilityTreshold': {
		'value': 0.45,
		'type': 'float'
	},
	'stayCompletlyOffline': {
		'value': False,
		'type': 'boolean'
	},
	'keepASROffline': {
		'value': False,
		'type': 'boolean'
	},
	'keepTTSOffline': {
		'value': False,
		'type': 'boolean'
	},
	'shortReplies': {
		'value': False,
		'type': 'boolean'
	},
	'whisperWhenSleeping': {
		'value': True,
		'type': 'boolean'
	},
	'newDeviceBroadcastPort': {
		'value': 12354,
		'type': 'integer'
	},
	'intentsOwner': {
		'value': '',
		'type': 'string'
	},
	'asr': 'snips',
	'tts': 'pico',
	'ttsLanguage': 'en-US',
	'ttsType': 'male',
	'ttsVoice': 'en-US', # The name of the voice on the TTS service
	'awsRegion': 'eu-central-1',
	'awsAccessKey': '',
	'awsSecretKey': '',
	'useSLC': False,
	'activeLanguage': 'en',
	'activeCountryCode': 'US',
	'moduleAutoUpdate': False,
	'githubUsername': '',
	'githubToken': '',
	'updateChannel': 'master',
	'supportedLanguages': {
		'en': {
			'snipsProjectId' : '',
			'default': True,
			'countryCode': 'US'
		},
		'fr': {
			'snipsProjectId' : '',
			'default': False,
			'countryCode': 'FR'
		},
		'de': {
			'snipsProjectId' : '',
			'default': False,
			'countryCode': 'DE'
		}
	},

	'snipsConsoleLogin': '',
	'snipsConsolePassword': '',

	'baseCurrency': {
		'value': 'CHF',
		'type': 'list',
		'data': ['CHF', 'EUR', 'USD', 'GBP', 'AUD']
	},

	'baseUnits': {
		'value': 'metric',
		'type': 'list',
		'data': ['metric', 'kelvin', 'imperial']
	},

	'onReboot': {
		'value': '',
		'type': 'string',
		'display': 'hidden'
	},

	'webInterfaceActive': {
		'value': False,
		'type': 'boolean'
	},
	'webInterfacePort': {
		'value': 5000,
		'type': 'integer'
	},
	'webInterfaceDevMode': {
		'value': False,
		'type': 'boolean'
	},

	#-----------------------
	# Modules
	#-----------------------

	'modules': {
		'Customisation': {
			'active'    : True,
			'version'   : 1.01,
			'author'    : 'ProjectAlice',
			'conditions': {
				'lang': [
					'en',
					'fr'
				]
			}
		}
	}
}
