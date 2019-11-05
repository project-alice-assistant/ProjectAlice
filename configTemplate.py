settings = {
	'notUnderstoodRetries': {
		'defaultValue': 3,
		'dataType': 'integer',
		'description': 'Defines how many times Alice will ask to repeat if not understood before she gives up'
	},
	'ssid': {
		'defaultValue': '',
		'dataType': 'string',
		'decription': 'Your Wifi name'
	},
	'wifipassword': {
		'defaultValue': '',
		'dataType': 'string',
		'descritption': 'Your Wifi password'
	},
	'mqttHost': {
		'defaultValue': 'localhost',
		'dataType': 'string'
	},
	'mqttPort': {
		'defaultValue': 1883,
		'dataType': 'integer'
	},
	'micSampleRate': {
		'defaultValue': 44100,
		'dataType': 'integer'
	},
	'micChannels': {
		'defaultValue': 1,
		'dataType': 'integer'
	},
	'enableDataStoring': {
		'defaultValue': False,
		'dataType': 'boolean'
	},
	'autoPruneStoredData': {
		'defaultValue': 0,
		'dataType': 'integer',
		'decription': 'Set to max entries to keep, 0 to disable pruning'
	},
	'probabilityTreshold': {
		'defaultValue': 0.45,
		'dataType': 'float'
	},
	'stayCompletlyOffline': {
		'defaultValue': False,
		'dataType': 'boolean'
	},
	'keepASROffline': {
		'defaultValue': False,
		'dataType': 'boolean'
	},
	'keepTTSOffline': {
		'defaultValue': False,
		'dataType': 'boolean'
	},
	'shortReplies': {
		'defaultValue': False,
		'dataType': 'boolean'
	},
	'whisperWhenSleeping': {
		'defaultValue': True,
		'dataType': 'boolean'
	},
	'newDeviceBroadcastPort': {
		'defaultValue': 12354,
		'dataType': 'integer'
	},
	'intentsOwner': {
		'defaultValue': '',
		'dataType': 'string'
	},
	'asr': {
		'defaultValue': 'snips',
		'dataType': 'list',
		'values': ['snips', 'google']
	},
	'tts': {
		'defaultValue': 'pico',
		'dataType': 'list',
		'values': ['pico', 'mycroft', 'amazon polly', 'google wavenet', 'snips makers']
	},
	'ttsLanguage': {
		'defaultValue': 'en-US',
		'dataType': 'string'
	},
	'ttsType': {
		'defaultValue': 'male',
		'dataType': 'list',
		'values': ['male', 'female']
	},
	'ttsVoice': {
		'defaultValue': 'en-US',
		'dataType': 'string'
	},
	'awsRegion': {
		'defaultValue': 'eu-central-1',
		'dataType': 'list',
		'values': ['eu-central-1', 'eu-west-1', ' eu-west-2', 'eu-west-3', 'eu-north-1', 'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2']
	},
	'awsAccessKey': {
		'defaultValue': '',
		'dataType': 'string'
	},
	'awsSecretKey': {
		'defaultValue': '',
		'dataType': 'password'
	},
	'useSLC': {
		'defaultValue': False,
		'dataType': 'boolean'
	},
	'activeLanguage': {
		'defaultValue': 'en',
		'dataType': 'list',
		'values': ['en', 'fr', 'de', 'it', 'pt']
	},
	'activeCountryCode': {
		'defaultValue': 'US',
		'dataType': 'string'
	},
	'moduleAutoUpdate': {
		'defaultValue': False,
		'dataType': 'boolean'
	},
	'githubUsername': {
		'defaultValue': '',
		'dataType': 'string'
	},
	'githubToken': {
		'defaultValue': '',
		'dataType': 'password'
	},
	'updateChannel': {
		'defaultValue': 'master',
		'dataType': 'list',
		'values': ['stable', 'release candidate', 'beta', 'alpha']
	},
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

	'snipsConsoleLogin': {
		'defaultValue': '',
		'dataType': 'string'
	},
	'snipsConsolePassword': {
		'defaultValue': '',
		'dataType': 'password'
	},

	'baseCurrency': {
		'defaultValue': 'CHF',
		'dataType': 'list',
		'values': ['CHF', 'EUR', 'USD', 'GBP', 'AUD']
	},

	'baseUnits': {
		'defaultValue': 'metric',
		'dataType': 'list',
		'values': ['metric', 'kelvin', 'imperial']
	},

	'onReboot': {
		'defaultValue': '',
		'dataType': 'string',
		'display': 'hidden'
	},

	'webInterfaceActive': {
		'defaultValue': False,
		'dataType': 'boolean'
	},
	'webInterfacePort': {
		'defaultValue': 5000,
		'dataType': 'integer'
	},
	'webInterfaceDevMode': {
		'defaultValue': False,
		'dataType': 'boolean'
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
