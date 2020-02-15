settings = {
	'autoReportSkillErrors': {
		'defaultValue': False,
		'dataType': 'boolean',
		'description': 'If true, an error thrown by a skill will automatically post a github issue and ping the author'
	},
	'notUnderstoodRetries' : {
		'defaultValue': 3,
		'dataType'    : 'integer',
		'description' : 'Defines how many times Alice will ask to repeat if not understood before she gives up'
	},
	'ssid'                 : {
		'defaultValue': '',
		'dataType'    : 'string',
		'description' : 'Your Wifi name'
	},
	'debug'                : {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'description' : 'If true debug logs will show'
	},
	'wifipassword'         : {
		'defaultValue': '',
		'dataType'    : 'password',
		'description' : 'Your Wifi password'
	},
	'mqttHost'             : {
		'defaultValue': 'localhost',
		'dataType'    : 'string',
		'description' : 'Mqtt server ip adress',
		'onUpdate'    : 'reconnectMqtt'
	},
	'mqttPort'             : {
		'defaultValue': 1883,
		'dataType'    : 'integer',
		'description' : 'Mqtt server port',
		'onUpdate'    : 'reconnectMqtt'
	},
	'mqttUser'             : {
		'defaultValue': '',
		'dataType'    : 'string',
		'description' : 'Mqtt user. Leave blank if not password protected',
		'onUpdate'    : 'reconnectMqtt'
	},
	'mqttPassword': {
		'defaultValue': '',
		'dataType'    : 'password',
		'description' : 'Mqtt password. Leave blank if not password protected',
		'onUpdate'    : 'reconnectMqtt'
	},
	'mqttTLSFile': {
		'defaultValue': '',
		'dataType'    : 'string',
		'description' : 'Mqtt TLS file path for SSL',
		'onUpdate'    : 'reconnectMqtt'
	},
	'micSampleRate': {
		'defaultValue': 44100,
		'dataType': 'integer',
		'description': 'Your microphone sample rate'
	},
	'micChannels': {
		'defaultValue': 1,
		'dataType': 'integer',
		'description': 'How many channel does your microphone support'
	},
	'enableDataStoring': {
		'defaultValue': False,
		'dataType': 'boolean',
		'description': 'Enables local telemetry data storing'
	},
	'autoPruneStoredData': {
		'defaultValue': 0,
		'dataType': 'integer',
		'description': 'Set to max entries to keep, 0 to disable pruning'
	},
	'probabilityThreshold': {
		'defaultValue': 0.45,
		'dataType': 'float',
		'description': 'Capture intents with lower probability score than this settings will trigger Alice not understood'
	},
	'stayCompletlyOffline': {
		'defaultValue': False,
		'dataType': 'boolean',
		'description': 'Nothing goes out! Well, that also means no skill updates, no access to web APIs'
	},
	'keepASROffline': {
		'defaultValue': True,
		'dataType': 'boolean',
		'description': 'Do not use any online ASR such as Google ASR'
	},
	'keepTTSOffline': {
		'defaultValue': True,
		'dataType': 'boolean',
		'description': 'Do not use any online TTS such as Google Wavenet or Amazon Polly'
	},
	'shortReplies': {
		'defaultValue': False,
		'dataType': 'boolean',
		'description': 'Use only short replies from Alice, when available'
	},
	'whisperWhenSleeping': {
		'defaultValue': True,
		'dataType': 'boolean',
		'description': 'Only available with Amazon Polly'
	},
	'newDeviceBroadcastPort': {
		'defaultValue': 12354,
		'dataType': 'integer',
		'description': 'Should be left as default, this is the port used to find new devices'
	},
	'intentsOwner': {
		'defaultValue': '',
		'dataType': 'string',
		'description': 'Your Snips account username'
	},
	'asr': {
		'defaultValue': 'pocketsphinx',
		'dataType'    : 'list',
		'values'      : ['pocketsphinx', 'google'],
		'description' : 'The ASR to use. Can\'t use an online ASR if you have set keepASROffline to true!'
	},
	'tts': {
		'defaultValue': 'pico',
		'dataType': 'list',
		'values': {'Pico': 'pico', 'Mycroft': 'mycroft', 'Amazon Polly': 'amazon', 'Google Wavenet': 'google', 'Snips Makers TTS': 'snips'},
		'description': 'The TTS to use. Can\'t use an online TTS if you have set keepTTSOffline!'
	},
	'ttsLanguage': {
		'defaultValue': 'en-US',
		'dataType': 'string',
		'description': 'Language for the TTS to use'
	},
	'ttsType': {
		'defaultValue': 'male',
		'dataType': 'list',
		'values': ['male', 'female'],
		'description': 'Choose the voice gender you want'
	},
	'ttsVoice'             : {
		'defaultValue': 'en-US',
		'dataType': 'string',
		'description': 'The voice the TTS should use. Find lists on respective TTS websites'
	},
	'awsRegion'            : {
		'defaultValue': 'eu-central-1',
		'dataType': 'list',
		'values': ['eu-central-1', 'eu-west-1', ' eu-west-2', 'eu-west-3', 'eu-north-1', 'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2'],
		'description': 'Region to use for Amazon Polly'
	},
	'awsAccessKey'         : {
		'defaultValue': '',
		'dataType'    : 'password',
		'description' : 'Your Amazon services access key'
	},
	'awsSecretKey'         : {
		'defaultValue': '',
		'dataType'    : 'password',
		'description' : 'Your Amazon services secret key'
	},
	'useHLC'               : {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'description' : 'Enables Hermes Led Control for visual feedback from your assistant'
	},
	'activeLanguage'       : {
		'defaultValue': 'en',
		'dataType'    : 'list',
		'values'      : ['en', 'fr', 'de', 'it', 'pt'],
		'description' : 'Project Alice active language'
	},
	'activeCountryCode'    : {
		'defaultValue': 'US',
		'dataType'    : 'string',
		'description' : 'Project Alice active country code'
	},
	'aliceAutoUpdate'      : {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'description' : 'Whether Alice should auto update, checked every hour'
	},
	'skillAutoUpdate': {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'description' : 'Whether skills should auto update, checked every 15 minutes'
	},
	'githubUsername': {
		'defaultValue': '',
		'dataType'    : 'string',
		'description' : 'Not mendatory, your github username and token allows you to use Github API much more, such as checking for skills, updating them etc etc'
	},
	'githubToken': {
		'defaultValue': '',
		'dataType'    : 'password',
		'description' : 'Not mendatory, your github username and token allows you to use Github API much more, such as checking for skills, updating them etc etc'
	},
	'aliceUpdateChannel': {
		'defaultValue': 'master',
		'dataType'    : 'list',
		'values'      : {'Stable': 'master', 'Release candidate': 'rc', 'Beta': 'beta', 'Alpha': 'alpha'},
		'description' : 'Choose your update frequency. Release is the only supposedly safe option! But if you like to live on the edge, alpha will allow you to preview what\'s coming next!'
	},
	'skillsUpdateChannel': {
		'defaultValue': 'master',
		'dataType'    : 'list',
		'values'      : {'Stable': 'master', 'Release candidate': 'rc', 'Beta': 'beta', 'Alpha': 'alpha'},
		'description' : 'Choose your skill update frequency. Release is the only supposedly safe option! But if you like to live on the edge, alpha will allow you to preview what\'s coming next!',
		'onUpdate'    : 'refreshStoreData'
	},
	'supportedLanguages': {
		'defaultValue': 'en',
		'dataType'    : 'list',
		'values'      : {
			'en': {
				'default': True,
				'countryCode': 'US'
			},
			'fr': {
				'default': False,
				'countryCode': 'FR'
			},
			'de': {
				'default': False,
				'countryCode': 'DE'
			}
		},
		'display': 'hidden'
	},

	'baseCurrency': {
		'defaultValue': 'CHF',
		'dataType': 'list',
		'values': ['CHF', 'EUR', 'USD', 'GBP', 'AUD'],
		'description': 'The currency used by Project Alice'
	},

	'baseUnits': {
		'defaultValue': 'metric',
		'dataType': 'list',
		'values': ['metric', 'kelvin', 'imperial'],
		'description': 'Units to use with Project Alice'
	},

	'nluEngine': {
		'defaultValue': 'snips',
		'dataType': 'list',
		'values': ['snips'],
		'description': 'Natural Language Understanding engine to use'
	},

	'onReboot': {
		'defaultValue': '',
		'dataType': 'string',
		'display': 'hidden'
	},

	'webInterfaceActive': {
		'defaultValue': True,
		'dataType': 'boolean',
		'description': 'Activates the web interface to be reached by browsing to x.x.x.x:webInterfacePort, e.g. 192.168.1.2:5000'
	},
	'webInterfacePort': {
		'defaultValue': 5000,
		'dataType': 'integer',
		'description': 'Change the web interface port to be used'
	},
	'devMode': {
		'defaultValue': False,
		'dataType': 'boolean',
		'description': 'Activates the developer part of the interface, for skill development'
	},

	# -----------------------
	# Skills
	# -----------------------

	'skills': {}
}
