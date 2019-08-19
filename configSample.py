"""
Use double quotes!
"""

settings = {
	"ssid": "",
	"wifipassword": "",
	"mqttHost": "localhost",
	"mqttPort": "1883",
	"micSampleRate": 44100,
	"micChannels": 1,
	"enableDataStoring": False,
	"autoPruneStoredData": 0, # Set to max entries to keep, 0 to disable pruning
	"probabilityTreshold": 0.45,
	"stayCompletlyOffline": False,
	"keepASROffline": False,
	"keepTTSOffline": False,
	"shortReplies": False,
	"whisperWhenSleeping": True,
	"newDeviceBroadcastPort": 12354,
	"intentsOwner": "",
	"webInterfaceActive": True,
	"asr": "snips",
	"tts": "pico",
	"ttsType": "male",
	"ttsVoice": "en-US",
	"awsRegion": "eu-central-1",
	"awsAccessKey": "",
	"awsSecretKey": "",
	"useSLC": False,
	"activeLanguage": "en",
	"moduleAutoUpdate": False,
	"supportedLanguages": {
		"en": {
			"snipsProjectId" : "",
			"default": True,
			"countryCode": 'US'
		},
		"fr": {
			"snipsProjectId" : "",
			"default": False,
			"countryCode": 'FR'
		},
		"de": {
			"snipsProjectId" : "",
			"default": False,
			"countryCode": 'DE'
		}
	},

	"snipsConsoleLogin": "",
	"snipsConsolePassword": "",

	"baseCurrency": "CHF",
	"baseUnits": "metric", # metric, kelvin or imperial

	"onReboot": "", # This is for system use only

	#-----------------------
	# Modules
	#-----------------------

	"modules": {
		"AliceCore": {
			"active"    : True,
			"version"   : 1.02,
			"author"    : "ProjectAlice",
			"conditions": {
				"lang": [
					"en",
					"fr"
				]
			}
		},
		"AliceSatellite": {
			"active"    : True,
			"version"   : 0.3,
			"author"    : "ProjectAlice",
			"conditions": {
				"lang": [
					"en",
					"fr"
				]
			}
		},
		"ContextSensitive": {
			"active"    : True,
			"version"   : 0.3,
			"author"    : "ProjectAlice",
			"conditions": {
				"lang": [
					"en",
					"fr"
				]
			}
		},
		"Customisation": {
			"active"    : True,
			"version"   : 0.2,
			"author"    : "ProjectAlice",
			"conditions": {
				"lang": [
					"en",
					"fr"
				]
			}
		},
		"DateDayTimeYear": {
			"active"    : True,
			"version"   : 0.35,
			"author"    : "Psychokiller1888",
			"conditions": {
				"lang": [
					"en",
					"fr",
					"de"
				]
			}
		},
		"RedQueen": {
			"active"    : True,
			"version"   : 0.7,
			"author"    : "ProjectAlice",
			"conditions": {
				"lang": [
					"en",
					"fr"
				]
			}
		}
	}
}
