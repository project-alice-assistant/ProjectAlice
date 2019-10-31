from core.base.model.ProjectAliceObject import ProjectAliceObject


class TasmotaConfigs(ProjectAliceObject):

	def getConfigs(self, deviceBrand: str, room: str) -> list:
		if deviceBrand not in self._configs:
			self.logError(f'[{self._name}] Devices brand "{deviceBrand}" unknown')
			return list()

		elif self._deviceType not in self._configs[deviceBrand]:
			self.logError(f'[{self._name}] Devices type "{self._deviceType}" unknown')
			return list()

		else:
			confs = self._configs[deviceBrand][self._deviceType].copy()
			for deviceConfs in confs:
				for conf in deviceConfs:
					conf['topic'] = conf['topic'].format(identifier=self._uid)
					conf['payload'] = conf['payload'].format(identifier=self._uid, room=room, type=self._deviceType)
			return confs


	def getBacklogConfigs(self, room: str) -> list:
		cmds = list()
		for cmdGroup in self._backlogConfigs:
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


	def __init__(self, deviceType: str, uid: str):
		super().__init__()
		self._name = 'TasmotaConfigs'

		self._deviceType = deviceType
		self._uid = uid

		self._backlogConfigs = [
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

		self._configs = {
			'wemos': {
				'switch': [
					[
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/Module',
							'payload': '18'
						}
					],
					[
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/MqttClient',
							'payload': 'switch_{room}'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/Gpio0',
							'payload': '9'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/Gpio12',
							'payload': '21'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/Prefix1',
							'payload': 'cmd'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/Prefix2',
							'payload': 'feedback'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/Prefix3',
							'payload': 'feedback'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/GroupTopic',
							'payload': 'all'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/TelePeriod',
							'payload': '0'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/FriendlyName',
							'payload': 'Switch - {room}'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/SwitchMode',
							'payload': '2'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/SwitchTopic',
							'payload': '0'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/Topic',
							'payload': '0'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/rule1',
							'payload': 'on switch1#state do publish projectalice/devices/tasmota/feedback/{identifier} {{"siteId":"{room}","deviceType":"{type}","feedback":%value%,"uid":"{identifier}"}} endon'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/rule1',
							'payload': '1'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/Restart',
							'payload': '1'
						}
					]
				],
				'pir'   : [
					[
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/Module',
							'payload': '18'
						}
					],
					[
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/MqttClient',
							'payload': 'PIR_{room}'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/Gpio0',
							'payload': '9'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/Gpio12',
							'payload': '21'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/FriendlyName',
							'payload': 'PIR - {room}'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/SwitchMode',
							'payload': '1'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/SwitchTopic',
							'payload': '0'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/rule1',
							'payload': 'on switch1#state do publish projectalice/devices/tasmota/feedback/{identifier} {{"siteId":"{room}","deviceType":"{type}","feedback":%value%,"uid":"{identifier}"}} endon'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/rule1',
							'payload': '1'
						},
						{
							'topic'  : 'projectalice/devices/tasmota/cmd/{identifier}/Restart',
							'payload': '1'
						}
					]
				]
			}
		}


	@property
	def deviceType(self) -> str:
		return self._deviceType


	@property
	def uid(self) -> str:
		return self._uid
