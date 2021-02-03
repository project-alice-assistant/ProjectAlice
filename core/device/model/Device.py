import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Union, Optional

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.device.model.DeviceAbility import DeviceAbility
from core.device.model.DeviceException import DeviceTypeUndefined
from core.device.model.DeviceType import DeviceType
from core.myHome.model.Location import Location
from core.webui.model.ClickReactionAction import ClickReactionAction
from core.webui.model.OnClickReaction import OnClickReaction


class Device(ProjectAliceObject):

	def __init__(self, data: Union[sqlite3.Row, Dict]):

		# settings: Holds the device display settings, such as x and y position, size and that stuff
		# deviceParams: Holds the device non declared params, such as sound muted and so on. These are not controlled values that can be completly random
		# deviceConfigs: Holds the device configurations, provided by the device's .config.template. These configs and values are controlled and cannot be random at all!
		super().__init__()

		if isinstance(data, sqlite3.Row):
			data = self.Commons.dictFromRow(data)

		self._data: dict = data
		self._id: int = data.get('id', -1)
		self._uid: str = data.get('uid', '')
		self._typeName: str = data.get('typeName', '')
		self._skillName: str = data.get('skillName', '')
		self._parentLocation: int = data.get('parentLocation', 0)
		self._deviceType: DeviceType = self.DeviceManager.getDeviceType(self._skillName, self._typeName)

		self._secret = ''  # Used to verify devices reply from UI

		if not self._deviceType:
			self.logError(f'Failed retrieving device type for device {self._typeName}')
			raise DeviceTypeUndefined(self._typeName)

		if not self._typeName:
			self._typeName = self._deviceType.deviceTypeName

		self._abilities: int = -1 if not data.get('abilities', None) else self.setAbilities(data['abilities'])
		self._deviceParams: Dict = json.loads(data.get('deviceParams', '{}')) if isinstance(
			data.get('deviceParams', '{}'), str) else data.get('deviceParams', dict())
		self._connected: bool = False

		# Settings are for UI, all the components use the same variable
		self._settings = json.loads(data.get('settings', '{}')) if isinstance(data.get('settings', '{}'),
																			  str) else data.get('settings', dict())
		settings = {
			'x': 0,
			'y': 0,
			'z': len(self.DeviceManager.devices),
			'w': 50,
			'h': 50,
			'r': 0
		}

		self._settings = {**settings, **self._settings}
		self._lastContact: int = 0

		self._deviceConfigs: Dict = json.loads(data.get('deviceConfigs', '{}'))
		self._loadConfigs()

		self._heartbeatRate = self._deviceConfigs.get('heartbeatRate')

		if self._id == -1:
			self.saveToDB()


	def onStart(self):
		super().onStart()
		self.skillInstance.registerDeviceInstance(self)


	def onStop(self):
		super().onStop()
		self.skillInstance.unregisterDeviceInstance(self)


	def onBooted(self):
		super().onBooted()


	def newSecret(self) -> str:
		"""
		Generates a new secret string
		:return:
		"""
		self._secret = str(uuid.uuid4())
		return self._secret


	def checkSecret(self, secret: str) -> bool:
		"""
		Checks if the given secret string matches the stored one and deletes the stored secret
		:param secret:
		:return:
		"""
		if not self._secret:
			self.logWarning(f'Device id **{self.id}** was asked to check secret but no secret set')
			return False

		if secret != self._secret:
			self.logWarning(f'Device id **{self.id}** replied with a wrong secret')
			return False

		self._secret = ''
		return True


	def _loadConfigs(self):
		self._deviceConfigs.setdefault('displayName', self._data.get('displayName', self._typeName))
		self._deviceConfigs.setdefault('heartbeatRate', self._deviceType.heartbeatRate)

		templates = self._deviceType.deviceConfigsTemplates
		changes = False
		for configName, configData in templates.items():
			if configName not in self._deviceConfigs:
				self.logInfo(f'Found new config for device **{self._deviceConfigs["displayName"]}**: {configName}')
				self._deviceConfigs[configName] = configData['defaultValue']
				changes = True

		for configName, configValue in self._deviceConfigs.copy().items():
			if configName == 'displayName' or configName == 'heartbeatRate':
				continue

			if configName not in templates:
				self.logInfo(f'Found a deprecated config for device **{self._deviceConfigs["displayName"]}**: {configName}')
				self._deviceConfigs.pop(configName, None)
				continue

			definition = templates[configName]
			if definition['dataType'] != 'list' and definition['dataType'] != 'longstring' and 'onInit' not in definition:
				if not isinstance(configValue, type(definition['defaultValue'])):
					changes = True
					try:
						# First try to cast the setting we have to the new type
						self._deviceConfigs[configName] = type(definition['defaultValue'])(configValue)
						self.logWarning(f'Existing configuration type missmatch: **{configName}**, cast variable to template configuration type')
					except Exception:
						# If casting failed let's fall back to the new default value
						self.logWarning(f'Existing configuration type missmatch: **{configName}**, replaced with template configuration')
						self._deviceConfigs[configName] = definition['defaultValue']
			elif definition['dataType'] == 'list' and 'onInit' not in definition:
				values = definition['values'].values() if isinstance(definition['values'], dict) else definition['values']

				if self._deviceConfigs[configName] and self._deviceConfigs[configName] not in values:
					changes = True
					self.logWarning(f'Selected value **{configValue}** for setting **{configName}** doesn\'t exist, reverted to default value --{definition["defaultValue"]}--')
					self._deviceConfigs[configName] = definition['defaultValue']

		if changes:
			self.saveToDB()


	def getAbilities(self) -> bin:
		"""
		Returns the device's abilities
		:return: a bitmask of the device's abilities
		"""
		if self._abilities == -1:
			return self._deviceType.abilities
		else:
			return self._abilities


	def hasAbilities(self, abilities: List[DeviceAbility]) -> bool:
		"""
		Checks if that device has the given abilities
		:param abilities: a list of DeviceAbility
		:return: boolean
		"""
		if self._abilities == -1:
			return self._deviceType.hasAbilities(abilities)
		else:
			check = 0
			for ability in abilities:
				check |= ability.value

			return self._abilities & check == check


	def setAbilities(self, abilities: List[DeviceAbility]):
		"""
		Sets this device's abilities, based on a bitmask
		:param abilities:
		:return:
		"""
		self._abilities = 0
		for ability in abilities:
			self._abilities |= ability.value


	# noinspection SqlResolve
	def saveToDB(self):
		"""
		Updates or inserts this device in DB
		:return:
		"""
		if self._id != -1:
			self.DatabaseManager.replace(
				tableName=self.DeviceManager.DB_DEVICE,
				query='REPLACE INTO :__table__ (id, uid, parentLocation, typeName, skillName, settings, deviceParams, deviceConfigs) VALUES (:id, :uid, :parentLocation, :typeName, :skillName, :settings, :deviceParams, :deviceConfigs)',
				callerName=self.DeviceManager.name,
				values={
					'id'             : self._id,
					'uid'            : self._uid,
					'parentLocation' : self._parentLocation,
					'typeName'       : self._typeName,
					'skillName'      : self._skillName,
					'settings'       : json.dumps(self._settings),
					'deviceParams'   : json.dumps(self._deviceParams),
					'deviceConfigs'  : json.dumps(self._deviceConfigs)
				}
			)
			self.publishDevice()
		else:
			deviceId = self.DatabaseManager.insert(
				tableName=self.DeviceManager.DB_DEVICE,
				callerName=self.DeviceManager.name,
				values={
					'uid'            : self._uid,
					'parentLocation' : self._parentLocation,
					'typeName'       : self._typeName,
					'skillName'      : self._skillName,
					'settings'       : json.dumps(self._settings),
					'deviceParams'   : json.dumps(self._deviceParams),
					'deviceConfigs'  : json.dumps(self._deviceConfigs)
				}
			)

			self._id = deviceId

	def getLocation(self) -> Optional[Location]:
		return self.LocationManager.getLocation(locId=self.parentLocation)


	def publishDevice(self):
		"""
		Whenever something changes on the device, the device data are published over mqtt
		to refresh the UI per exemple
		:return:
		"""
		self.MqttManager.publish(constants.TOPIC_DEVICE_UPDATED, payload={'uid': self._uid, 'device': self.toDict()})


	def pairingDone(self, uid: str):
		"""
		Called whenever a pairing procedure succeeded
		:param uid: the attributed uid
		:return:
		"""
		self._uid = uid
		self.saveToDB()


	def onDeviceUIReply(self, data: dict):
		"""
		When a device is clicked in the UI, it receive an optional reply directive that calls this method
		:param data:
		:return:
		"""
		pass # Implemented by childs


	@property
	def settings(self) -> dict:
		return self._settings


	@property
	def connected(self) -> bool:
		"""
		Returns wheather or not this device is connected
		:return:
		"""
		return self._connected


	@connected.setter
	def connected(self, value: bool):
		"""
		Sets device connection status
		:param value: bool
		:return:
		"""
		self._connected = value


	@property
	def paired(self) -> bool:
		"""
		A device is paired when it has a valid UID
		:return:
		"""
		try:
			uuid.UUID(str(self._uid))
			return True
		except ValueError:
			return False


	@property
	def heartbeatRate(self) -> int:
		return self._deviceConfigs.get('heartbeatRate')


	@property
	def deviceTypeName(self) -> str:
		return self._typeName


	@property
	def deviceType(self) -> DeviceType:
		return self._deviceType


	@property
	def parentLocation(self) -> int:
		return self._parentLocation


	@parentLocation.setter
	def parentLocation(self, value: int):
		self._parentLocation = value


	@property
	def skillName(self) -> str:
		return self._skillName


	@property
	def id(self) -> int:
		return self._id


	@property
	def uid(self) -> str:
		return self._uid


	@property
	def displayName(self) -> str:
		return self._deviceConfigs['displayName']


	@property
	def skillInstance(self):
		return self.SkillManager.getSkillInstance(self._skillName)


	def toDict(self) -> dict:
		return {
			'abilities'             : bin(self.getAbilities()),
			'connected'             : self._connected,
			'deviceParams'          : self._deviceParams,
			'settings'              : self._settings,
			'deviceConfigs'         : self._deviceConfigs,
			'id'                    : self._id,
			'lastContact'           : self._lastContact,
			'parentLocation'        : self._parentLocation,
			'skillName'             : self._skillName,
			'typeName'              : self._typeName,
			'uid'                   : self._uid,
			'allowHeartbeatOverride': self.deviceType.allowHeartbeatOverride
		}


	def getDeviceIcon(self) -> Path:
		"""
		Return the path of the icon representing the current status of the device
		e.g. a light bulb can be on or off and display its status
		:return: the icon file path
		"""
		return Path(f'{self.Commons.rootDir()}/skills/{self.skillName}/devices/img/{self._typeName}.png')


	def updateSettings(self, settings: dict):
		self._settings = {**self._settings, **settings}


	def updateConfigs(self, configs: dict):
		self._deviceConfigs = {**self._deviceConfigs, **configs}


	def getParam(self, key: str, default: Any = False) -> Any:
		return self._deviceParams.get(key, default)


	def updateParams(self, key: str, value: Any):
		self._deviceParams[key] = value
		self.saveToDB()


	def onUIClick(self) -> dict:
		"""
		Called whenever a device's icon is clicked on the UI
		:return:
		"""
		if not self.paired:
			self.DeviceManager.startBroadcastingForNewDevice(self)
			reaction = OnClickReaction(
				action=ClickReactionAction.INFO_NOTIFICATION.value,
				data='notifications.info.pleasePlugDevice'
			)
			return reaction.toDict()

		return OnClickReaction(action=ClickReactionAction.NONE.value).toDict()


	def linkedTo(self, targetLocation: int) -> bool:
		"""
		Checks if this device is linked to the given location
		:param targetLocation: int
		:return: bool
		"""
		for link in self.DeviceManager.deviceLinks.values():
			if link.deviceId == self.id and link.targetLocation == targetLocation:
				return True
		return False


	def getLinks(self) -> dict:
		links = dict()
		for link in self.DeviceManager.deviceLinks.values():
			if link.deviceId == self.id:
				links[link.id] = link
		return links


	def __repr__(self):
		return f'Device({self._id} - {self._deviceConfigs["displayName"]}, uid({self._uid}), Location({self._parentLocation}))'


	def __eq__(self, other):
		return other and self._uid == other.uid


	@classmethod
	def getDeviceTypeDefinition(cls) -> dict:
		raise NotImplementedError
