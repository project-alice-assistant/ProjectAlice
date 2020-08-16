settings = {
	'delegateNluTraining': {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'When activated, the NLU training part will not happen on this device but delegated to another device of your mqtt network.',
		'category'    : 'nlu'
	},
	'timezone': {
		'defaultValue': 'Europe/Zurich',
		'dataType'    : 'string',
		'isSensitive' : False,
		'description' : 'Your timezone',
		'beforeUpdate': 'updateTimezone',
		'category'    : 'system'
	},
	'asoundConfig': {
		'defaultValue': '',
		'dataType'    : 'longstring',
		'isSensitive' : False,
		'description' : 'Your asound settings',
		'beforeUpdate': 'injectAsound',
		'category'    : 'system'
	},
	'recordAudioAfterWakeword': {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'Allow audio record after a wakeword is detected to keep the last user speech. Can be usefull for recording skills',
		'category'    : 'system'
	},
	'deviceName'              : {
		'defaultValue': 'default',
		'dataType'    : 'string',
		'isSensitive' : False,
		'description' : 'Name this Alice unit. It is good practice to use a room/location name to name your devices.',
		'category'    : 'device'
	},
	'sessionTimeout'          : {
		'defaultValue': 10,
		'dataType'    : 'integer',
		'isSensitive' : False,
		'description' : 'Defines the number of seconds before a session times out for inactivity',
		'category'    : 'device'
	},
	'adminPinCode'            : {
		'defaultValue': 1234,
		'dataType'    : 'integer',
		'isSensitive' : True,
		'description' : 'Admin pin code, only numbers, 4 digits',
		'beforeUpdate': 'checkNewAdminPinCode',
		'onUpdate'    : 'updateAdminPinCode',
		'category'    : 'system'
	},
	'ibmCloudAPIKey'          : {
		'defaultValue': '',
		'dataType'    : 'string',
		'isSensitive' : True,
		'description' : 'API key for IBM Cloud Watson Tts and ASR',
		'category'    : 'credentials'
	},
	'ibmCloudAPIURL'          : {
		'defaultValue': '',
		'dataType'    : 'string',
		'isSensitive' : False,
		'description' : 'API url for IBM Cloud Watson Tts and ASR',
		'category'    : 'credentials'
	},
	'autoReportSkillErrors'   : {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'If true, an error thrown by a skill will automatically post a github issue and ping the author',
		'category'    : 'system'
	},
	'disableSoundAndMic'      : {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'If this device is a server without sound and mic, turn this to True',
		'onUpdate'    : 'enableDisableSound',
		'category'    : 'device'
	},
	'notUnderstoodRetries'    : {
		'defaultValue': 3,
		'dataType'    : 'integer',
		'isSensitive' : False,
		'description' : 'Defines how many times Alice will ask to repeat if not understood before she gives up',
		'category'    : 'system'
	},
	'ssid'                    : {
		'defaultValue': '',
		'dataType'    : 'string',
		'isSensitive' : False,
		'description' : 'Your Wifi name',
		'category'    : 'device'
	},
	'debug'                   : {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'If true debug logs will show',
		'onUpdate'    : 'toggleDebugLogs',
		'category'    : 'system'
	},
	'wifipassword'            : {
		'defaultValue': '',
		'dataType'    : 'string',
		'isSensitive' : True,
		'description' : 'Your Wifi password',
		'category'    : 'device'
	},
	'mqttHost'                : {
		'defaultValue': 'localhost',
		'dataType'    : 'string',
		'isSensitive' : False,
		'description' : 'Mqtt server ip adress',
		'onUpdate'    : 'updateMqttSettings',
		'category'    : 'mqtt'
	},
	'mqttPort'                : {
		'defaultValue': 1883,
		'dataType'    : 'integer',
		'isSensitive' : False,
		'description' : 'Mqtt server port',
		'onUpdate'    : 'updateMqttSettings',
		'category'    : 'mqtt'
	},
	'mqttUser'                : {
		'defaultValue': '',
		'dataType'    : 'string',
		'isSensitive' : False,
		'description' : 'Mqtt user. Leave blank if not password protected',
		'onUpdate'    : 'updateMqttSettings',
		'category'    : 'mqtt'
	},
	'mqttPassword'            : {
		'defaultValue': '',
		'dataType'    : 'string',
		'isSensitive' : True,
		'description' : 'Mqtt password. Leave blank if not password protected',
		'onUpdate'    : 'updateMqttSettings',
		'category'    : 'mqtt'
	},
	'mqttTLSFile'             : {
		'defaultValue': '',
		'dataType'    : 'string',
		'isSensitive' : False,
		'description' : 'Mqtt TLS file path for SSL',
		'onUpdate'    : 'updateMqttSettings',
		'category'    : 'mqtt'
	},
	'enableDataStoring'       : {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'Enables local telemetry data storing',
		'category'    : 'system'
	},
	'autoPruneStoredData'     : {
		'defaultValue': 0,
		'dataType'    : 'integer',
		'isSensitive' : False,
		'description' : 'Set to max entries to keep, 0 to disable pruning',
		'category'    : 'system'
	},
	'probabilityThreshold'    : {
		'defaultValue': 0.45,
		'dataType'    : 'float',
		'isSensitive' : False,
		'description' : 'Captured intents with lower probability score than this settings will trigger Alice not understood',
		'category'    : 'system'
	},
	'stayCompletlyOffline'    : {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'Nothing goes out! Well, that also means no skill updates, no access to web APIs',
		'category'    : 'system'
	},
	'keepASROffline'          : {
		'defaultValue': True,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'Do not use any online Asr such as Google Asr',
		'category'    : 'asr'
	},
	'keepTTSOffline'          : {
		'defaultValue': True,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'Do not use any online Tts such as Google Wavenet or Amazon Polly',
		'category'    : 'tts'
	},
	'shortReplies'            : {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'Use only short replies from Alice, when available',
		'category'    : 'system'
	},
	'whisperWhenSleeping'     : {
		'defaultValue': True,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'Only available with Amazon Polly',
		'category'    : 'tts'
	},
	'newDeviceBroadcastPort'  : {
		'defaultValue': 12354,
		'dataType'    : 'integer',
		'isSensitive' : False,
		'description' : 'Should be left as default, this is the port used to find new devices',
		'category'    : 'device'
	},
	'asr'                     : {
		'defaultValue': 'deepspeech',
		'dataType'    : 'list',
		'isSensitive' : False,
		'values'      : ['deepspeech', 'pocketsphinx', 'google', 'snips'],
		'description' : 'The Asr to use. Can\'t use an online Asr if you have set keepASROffline to true!',
		'onUpdate'    : 'reloadASR',
		'category'    : 'asr'
	},
	'asrFallback'             : {
		'defaultValue': 'pocketsphinx',
		'dataType'    : 'list',
		'isSensitive' : False,
		'values'      : ['deepspeech', 'pocketsphinx', 'google', 'snips'],
		'description' : 'The Asr to use in case the default ASR becomes unavailable',
		'category'    : 'asr'
	},
	'asrTimeout'              : {
		'defaultValue': 10,
		'dataType'    : 'integer',
		'isSensitive' : False,
		'description' : 'Defines after how many seconds the Asr times out',
		'category'    : 'asr'
	},
	'wakewordEngine'          : {
		'defaultValue': 'snips',
		'dataType'    : 'list',
		'isSensitive' : False,
		'values'      : ['porcupine', 'snips', 'precise'],
		'description' : 'Wakeword engine to use',
		'category'    : 'wakeword',
		'onUpdate'    : 'reloadWakeword'
	},
	'wakewordSensitivity'     : {
		'defaultValue': 0.5,
		'dataType'    : 'range',
		'min'         : 0,
		'max'         : 1,
		'step'        : 0.01,
		'isSensitive' : False,
		'description' : 'Default wakeword sensitivity',
		'category'    : 'wakeword',
		'onUpdate'    : 'restartWakewordEngine'
	},
	'tts'                     : {
		'defaultValue': 'pico',
		'dataType'    : 'list',
		'isSensitive' : False,
		'values'      : {'Pico': 'pico', 'Mycroft': 'mycroft', 'Amazon Polly': 'amazon', 'Google Wavenet': 'google', 'IBM Watson': 'watson'},
		'description' : 'The Tts to use. Can\'t use an online Tts if you have set keepTTSOffline!',
		'onUpdate'    : 'reloadTTS',
		'category'    : 'tts'
	},
	'ttsFallback': {
		'defaultValue': 'pico',
		'dataType'    : 'list',
		'isSensitive' : False,
		'values'      : {'Pico': 'pico', 'Mycroft': 'mycroft', 'Amazon Polly': 'amazon', 'Google Wavenet': 'google', 'IBM Watson': 'watson'},
		'description' : 'The Tts to use in case the default Tts becomes unavailable.',
		'onUpdate'    : 'reloadTTS',
		'category'    : 'tts'
	},
	'ttsLanguage'             : {
		'defaultValue': 'en-US',
		'dataType'    : 'string',
		'isSensitive' : False,
		'description' : 'Language for the Tts to use',
		'help'        : 'PICO VOICE<br>AMAZON POLLY<br>MYCROFT<br>GOOGLE WAVENET<br>IBM WATSON',
		'onUpdate'    : 'reloadTTS',
		'category'    : 'tts'
	},
	'ttsType'                 : {
		'defaultValue': 'male',
		'dataType'    : 'list',
		'isSensitive' : False,
		'values'      : ['male', 'female'],
		'description' : 'Choose the voice gender you want',
		'onUpdate'    : 'reloadTTS',
		'category'    : 'tts'
	},
	'ttsVoice'                : {
		'defaultValue': 'en-US',
		'dataType'    : 'string',
		'isSensitive' : False,
		'description' : 'The voice the Tts should use. Find lists on respective Tts websites',
		'onUpdate'    : 'reloadTTS',
		'category'    : 'tts'
	},
	'awsRegion'               : {
		'defaultValue': 'eu-central-1',
		'dataType'    : 'list',
		'isSensitive' : False,
		'values'      : [
			'eu-north-1',
			'ap-south-1',
			'eu-west-3',
			'eu-west-2',
			'eu-west-1',
			'ap-northeast-2',
			'me-south-1',
			'ap-northeast-1',
			'sa-east-1',
			'ca-central-1',
			'ap-east-1',
			'ap-southeast-1',
			'ap-southeast-2',
			'eu-central-1',
			'us-east-1',
			'us-east-2',
			'us-west-1',
			'us-west-2'
		],
		'description' : 'Region to use for Amazon Polly',
		'category'    : 'credentials'
	},
	'awsAccessKey'            : {
		'defaultValue': '',
		'dataType'    : 'string',
		'isSensitive' : True,
		'description' : 'Your Amazon services access key',
		'category'    : 'credentials'
	},
	'awsSecretKey'            : {
		'defaultValue': '',
		'dataType'    : 'string',
		'isSensitive' : True,
		'description' : 'Your Amazon services secret key',
		'category'    : 'credentials'
	},
	'useHLC'                  : {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'Enables Hermes Led Control for visual feedback from your assistant',
		'category'    : 'system'
	},
	'activeLanguage'          : {
		'defaultValue': 'en',
		'dataType'    : 'list',
		'isSensitive' : False,
		'values'      : ['en', 'fr', 'de', 'it', 'pt'],
		'description' : 'Project Alice active language',
		'category'    : 'system'
	},
	'activeCountryCode'       : {
		'defaultValue': 'US',
		'dataType'    : 'string',
		'isSensitive' : False,
		'description' : 'Project Alice active country code',
		'category'    : 'system'
	},
	'nonNativeSupportLanguage': {
		'defaultValue': '',
		'dataType'    : 'string',
		'isSensitive' : False,
		'description' : 'If you want to use a non natively supported language, set it here.',
		'category'    : 'system'
	},
	'nonNativeSupportCountry' : {
		'defaultValue': '',
		'dataType'    : 'string',
		'isSensitive' : False,
		'description' : 'If you want to use a non natively supported country, set it here.',
		'category'    : 'system'
	},
	'aliceAutoUpdate'         : {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'Whether Alice should auto update, checked every hour',
		'category'    : 'system'
	},
	'skillAutoUpdate'         : {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'Whether skills should auto update, checked every 15 minutes',
		'category'    : 'system'
	},
	'githubUsername'          : {
		'defaultValue': '',
		'dataType'    : 'string',
		'isSensitive' : False,
		'description' : 'Not mendatory, your github username and token allows you to use Github API much more, such as checking for skills, updating them etc etc',
		'category'    : 'credentials'
	},
	'githubToken'             : {
		'defaultValue': '',
		'dataType'    : 'string',
		'isSensitive' : True,
		'description' : 'Not mendatory, your github username and token allows you to use Github API much more, such as checking for skills, updating them etc etc',
		'category'    : 'credentials'
	},
	'aliceUpdateChannel'      : {
		'defaultValue': 'master',
		'dataType'    : 'list',
		'isSensitive' : False,
		'values'      : {'Stable': 'master', 'Release candidate': 'rc', 'Beta': 'beta', 'Alpha': 'alpha'},
		'description' : 'Choose your update frequency. Release is the only supposedly safe option! But if you like to live on the edge, alpha will allow you to preview what\'s coming next!',
		'category'    : 'system'
	},
	'skillsUpdateChannel'     : {
		'defaultValue': 'master',
		'dataType'    : 'list',
		'isSensitive' : False,
		'values'      : {'Stable': 'master', 'Release candidate': 'rc', 'Beta': 'beta', 'Alpha': 'alpha'},
		'description' : 'Choose your skill update frequency. Release is the only supposedly safe option! But if you like to live on the edge, alpha will allow you to preview what\'s coming next!',
		'onUpdate'    : 'refreshStoreData',
		'category'    : 'system'
	},
	'supportedLanguages'      : {
		'defaultValue': {
			'en': {
				'default'           : True,
				'defaultCountryCode': 'US',
				'countryCodes'      : ['US', 'GB', 'AU']
			},
			'fr': {
				'default'           : False,
				'defaultCountryCode': 'FR',
				'countryCodes'      : ['FR', 'CH']
			},
			'de': {
				'default'           : False,
				'defaultCountryCode': 'DE',
				'countryCodes'      : ['DE', 'CH']
			},
			'it': {
				'default'           : False,
				'defaultCountryCode': 'IT',
				'countryCodes'      : ['IT', 'CH']
			}
		},
		'dataType'    : 'list',
		'isSensitive' : False,
		'values'      : {
			'en': {
				'default'           : True,
				'defaultCountryCode': 'US',
				'countryCodes'      : ['US', 'GB', 'AU']
			},
			'fr': {
				'default'           : False,
				'defaultCountryCode': 'FR',
				'countryCodes'      : ['FR', 'CH']
			},
			'de': {
				'default'           : False,
				'defaultCountryCode': 'DE',
				'countryCodes'      : ['DE', 'CH']
			},
			'it': {
				'default'           : False,
				'defaultCountryCode': 'IT',
				'countryCodes'      : ['IT', 'CH']
			}
		},
		'display'     : 'hidden',
		'category'    : 'system'
	},
	'baseCurrency'            : {
		'defaultValue': 'CHF',
		'dataType'    : 'list',
		'isSensitive' : False,
		'values'      : ['CHF', 'EUR', 'USD', 'GBP', 'AUD'],
		'description' : 'The currency used by Project Alice',
		'category'    : 'system'
	},
	'baseUnits'               : {
		'defaultValue': 'metric',
		'dataType'    : 'list',
		'isSensitive' : False,
		'values'      : ['metric', 'kelvin', 'imperial'],
		'description' : 'Units to use with Project Alice',
		'category'    : 'system'
	},
	'nluEngine'               : {
		'defaultValue': 'snips',
		'dataType'    : 'list',
		'isSensitive' : False,
		'values'      : ['snips'],
		'description' : 'Natural Language Understanding engine to use',
		'category'    : 'nlu'
	},
	'onReboot'                : {
		'defaultValue': '',
		'dataType'    : 'string',
		'isSensitive' : False,
		'display'     : 'hidden',
		'category'    : 'system'
	},
	'webInterfaceActive'      : {
		'defaultValue': True,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'Activates the web interface to be reached by browsing to x.x.x.x:webInterfacePort, e.g. 192.168.1.2:5000',
		'category'    : 'system'
	},
	'webInterfacePort'        : {
		'defaultValue': 5000,
		'dataType'    : 'integer',
		'isSensitive' : False,
		'description' : 'Change the web interface port to be used',
		'category'    : 'system'
	},
	'devMode'                 : {
		'defaultValue': False,
		'dataType'    : 'boolean',
		'isSensitive' : False,
		'description' : 'Activates the developer part of the interface, for skill development',
		'category'    : 'system'
	}
}
