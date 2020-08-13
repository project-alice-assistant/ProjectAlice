from core.base.model.ProjectAliceObject import ProjectAliceObject


class TasmotaConfigs(ProjectAliceObject):

	def __init__(self, deviceType: str, uid: str):
		super().__init__()
		self._name = 'TasmotaConfigs'

		self._deviceType = deviceType
		self._uid = uid


	@property
	def deviceType(self) -> str:
		return self._deviceType


	@property
	def uid(self) -> str:
		return self._uid


	def getConfigs(self, deviceBrand: str, room: str) -> list:
		if deviceBrand not in self.CONFIGS:
			self.logError(f'[{self._name}] Devices brand "{deviceBrand}" unknown')
			return list()

		elif self._deviceType not in self.CONFIGS[deviceBrand]:
			self.logError(f'[{self._name}] Devices type "{self._deviceType}" unknown')
			return list()

		else:
			confs = self.CONFIGS[deviceBrand][self._deviceType].copy()
			for deviceConfs in confs:
				for conf in deviceConfs:
					conf['topic'] = conf['topic'].format(identifier=self._uid)
					conf['payload'] = conf['payload'].format(identifier=self._uid, room=room, type=self._deviceType)
			return confs


	def getBacklogConfigs(self, room: str) -> list:
		cmds = list()
		for cmdGroup in self.BACKLOG_CONFIGS:
			group = dict()
			group['cmds'] = [cmd.format(
				mqtthost=self.Commons.getLocalIp(),
				identifier=self._uid,
				room=room,
				type=self._deviceType,
				ssid=self.ConfigManager.getAliceConfigByName('ssid'),
				wifipass=self.ConfigManager.getAliceConfigByName('wifipassword')
			) for cmd in cmdGroup['cmds']]

			group['waitAfter'] = cmdGroup['waitAfter']
			cmds.append(group)

		return cmds


	def getTasmotaDownloadLink(self) -> str:
		if self._deviceType in self.SPECIFIC_VERSIONS:
			return self.SPECIFIC_VERSIONS[self._deviceType]
		return 'https://github.com/arendst/Tasmota/releases/download/v8.3.1/tasmota.bin'


	SPECIFIC_VERSIONS = {
		'envSensor': 'https://github.com/arendst/Tasmota/releases/download/v8.3.1/tasmota-sensors.bin'
	}


	BACKLOG_CONFIGS = [
		{
			'cmds'     : [
				'ssid1 {ssid}',
				'password1 {wifipass}'
			],
			'waitAfter': 15
		},
		{
			'cmds'     : [
				'MqttHost {mqtthost}',
				'MqttClient {type}_{room}',
				'TelePeriod 0',
				'module 18'
			],
			'waitAfter': 8
		},
		{
			'cmds'     : [
				'gpio0 9',
				'gpio12 21'
			],
			'waitAfter': 8
		},
		{
			'cmds'     : [
				'friendlyname {type} - {room}'
			],
			'waitAfter': 8
		},
		{
			'cmds'     : [
				'switchmode 2',
				'switchtopic 0'
			],
			'waitAfter': 8
		},
		{
			'cmds'     : [
				'topic {identifier}',
				'grouptopic all',
				'fulltopic projectalice/devices/tasmota/%prefix%/%topic%/',
				'prefix1 cmd',
				'prefix2 feedback',
				'prefix3 feedback'
			],
			'waitAfter': 8
		},
		{
			'cmds'     : [
				'rule1 on System#Boot do publish projectalice/devices/tasmota/feedback/hello/{identifier} {{"siteId":"{room}","deviceType":"{type}","uid":"{identifier}"}} endon',
				'rule1 1',
				'rule2 on switch1#state do publish projectalice/devices/tasmota/feedback/{identifier} {{"siteId":"{room}","deviceType":"{type}","feedback":%value%,"uid":"{identifier}"}} endon',
				'rule2 1',
				'restart 1'
			],
			'waitAfter': 5
		}
	]

	BASE_TOPIC = 'projectalice/devices/tasmota/cmd/{identifier}'

	CONFIGS = {
		'wemos': {
			'switch': [
				[
					{
						'topic'  : BASE_TOPIC + '/Module',
						'payload': '18'
					}
				],
				[
					{
						'topic'  : BASE_TOPIC + '/MqttClient',
						'payload': 'switch_{room}'
					},
					{
						'topic'  : BASE_TOPIC + '/Gpio0',
						'payload': '9'
					},
					{
						'topic'  : BASE_TOPIC + '/Gpio12',
						'payload': '21'
					},
					{
						'topic'  : BASE_TOPIC + '/Prefix1',
						'payload': 'cmd'
					},
					{
						'topic'  : BASE_TOPIC + '/Prefix2',
						'payload': 'feedback'
					},
					{
						'topic'  : BASE_TOPIC + '/Prefix3',
						'payload': 'feedback'
					},
					{
						'topic'  : BASE_TOPIC + '/GroupTopic',
						'payload': 'all'
					},
					{
						'topic'  : BASE_TOPIC + '/TelePeriod',
						'payload': '0'
					},
					{
						'topic'  : BASE_TOPIC + '/FriendlyName',
						'payload': 'Switch - {room}'
					},
					{
						'topic'  : BASE_TOPIC + '/SwitchMode',
						'payload': '2'
					},
					{
						'topic'  : BASE_TOPIC + '/SwitchTopic',
						'payload': '0'
					},
					{
						'topic'  : BASE_TOPIC + '/Topic',
						'payload': '0'
					},
					{
						'topic'  : BASE_TOPIC + '/rule1', #NOSONAR
						'payload': 'on switch1#state do publish projectalice/devices/tasmota/feedback/{identifier} {{"siteId":"{room}","deviceType":"{type}","feedback":%value%,"uid":"{identifier}"}} endon'
					},
					{
						'topic'  : BASE_TOPIC + '/rule1', #NOSONAR
						'payload': '1'
					},
					{
						'topic'  : BASE_TOPIC + '/Restart',
						'payload': '1'
					}
				]
			],
			'pir'   : [
				[
					{
						'topic'  : BASE_TOPIC + '/Module',
						'payload': '18'
					}
				],
				[
					{
						'topic'  : BASE_TOPIC + '/MqttClient',
						'payload': 'PIR_{room}'
					},
					{
						'topic'  : BASE_TOPIC + '/Gpio0',
						'payload': '9'
					},
					{
						'topic'  : BASE_TOPIC + '/Gpio12',
						'payload': '21'
					},
					{
						'topic'  : BASE_TOPIC + '/FriendlyName',
						'payload': 'PIR - {room}'
					},
					{
						'topic'  : BASE_TOPIC + '/SwitchMode',
						'payload': '1'
					},
					{
						'topic'  : BASE_TOPIC + '/SwitchTopic',
						'payload': '0'
					},
					{
						'topic'  : BASE_TOPIC + '/rule1', #NOSONAR
						'payload': 'on switch1#state do publish projectalice/devices/tasmota/feedback/{identifier} {{"siteId":"{room}","deviceType":"{type}","feedback":%value%,"uid":"{identifier}"}} endon'
					},
					{
						'topic'  : BASE_TOPIC + '/rule1', #NOSONAR
						'payload': '1'
					},
					{
						'topic'  : BASE_TOPIC + '/Restart',
						'payload': '1'
					}
				]
			]
		}
	}
