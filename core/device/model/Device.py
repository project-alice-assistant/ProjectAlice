import json
import sqlite3
from typing import Dict, List, Optional, Union

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.device.model.DeviceAbility import DeviceAbility
from core.device.model.DeviceException import DeviceTypeUndefined
from core.device.model.DeviceType import DeviceType
from core.myHome.model.Location import Location


class Device(ProjectAliceObject):

	def __init__(self, data: Union[sqlite3.Row, Dict]):
		super().__init__()

		if isinstance(data, sqlite3.Row):
			data = self.Commons.dictFromRow(data)

		self._data: dict = data
		self._id: str = data.get('id', -1)
		self._uid: str = data['uid']
		self._typeName:str = data.get('typeName', '')
		self._skillName: str = data.get('skillName', '')
		self._locationId: int = data.get('locationId', 0)
		self._deviceType: DeviceType = self.DeviceManager.getDeviceType(self._skillName, self._typeName)
		self._abilities: int = 0 if not data.get('abilities', None) else self.setAbilities(data['abilities'])
		self._deviceParams: Dict = json.loads(data.get('deviceParams', '{}'))
		self._displayName: str = data.get('displayName', '')
		self._connected: bool = False

		self._displaySettings = json.loads(data.get('displaySettings', '{}')) if isinstance(data.get('displaySettings', '{}'), str) else data.get('settings', dict())
		settings = {
			'x': 0,
			'y': 0,
			'z': len(self.LocationManager.locations),
			'w': 50,
			'h': 50,
			'r': 0
		}

		self._displaySettings = {**settings, **self._displaySettings}
		self._lastContact: int = 0

		if not self._displayName:
			self._displayName = self._typeName

		if self._id == -1:
			self.saveToDB()


	def hasAbilities(self, abilities: List[DeviceAbility]) -> bool:
		"""
		Checks if that device has the given abilities
		:param abilities: a list of DeviceAbility
		:return: boolean
		"""
		if self._abilities == 0:
			return self._deviceType.hasAbilities(abilities)
		else:
			check = 0
			for ability in abilities:
				check |= ability.value

			return self._abilities & check == check


	def setAbilities(self, abilities: List[DeviceAbility]):
		"""
		Sets this device's abilities, basd on a bitmask
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
				query='REPLACE INTO :__table__ (id, uid, locationId, type, skillname, displaySettings, displayName, deviceParams) VALUES (:id, :uid, :locationId, :type, :skillname, :displaySettings, :displayName, :deviceParams)',
				callerName=self.DeviceManager.name,
				values={
					'id'             : self._id,
					'uid'            : self._uid,
					'locationId'     : self._locationId,
					'typeName'       : self._typeName,
					'skillName'      : self._skillName,
					'displaySettings': json.dumps(self._displaySettings),
					'displayName'    : self._displayName,
					'deviceParams'   : json.dumps(self._deviceParams)
				}
			)
		else:
			deviceId = self.DatabaseManager.insert(
				tableName=self.DeviceManager.DB_DEVICE,
				callerName=self.DeviceManager.name,
				values={
					'uid'            : self._uid,
					'locationId'     : self._locationId,
					'typeName'       : self._typeName,
					'skillName'      : self._skillName,
					'displaySettings': json.dumps(self._displaySettings),
					'displayName'    : self._displayName,
					'deviceParams'   : json.dumps(self._deviceParams)
				}
			)

			self._id = deviceId


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
	def strType(self) -> str:
		return self._typeName


	@property
	def deviceType(self) -> DeviceType:
		return self._deviceType


	@property
	def locationId(self) -> int:
		return self._locationId


	@locationId.setter
	def locationId(self, value: int):
		self._locationId = value
		self._locationId = value


	@property
	def skillName(self) -> str:
		return self._skillName


	@property
	def uid(self) -> str:
		return self._uid


	def __repr__(self):
		return f'Device({self._id} - {self._displayName}, uid({self._uid}), Location({self._locationId}))'

	def __eq__(self, other):
		return other and self._uid == other.uid











	def replace(self, needle: str, haystack: str) -> str:
		return self.name.replace(needle, haystack)


	def clearUid(self):
		self.uid = ''
		self.DatabaseManager.update(tableName=self.DeviceManager.DB_DEVICE,
		                            callerName=self.DeviceManager.name,
		                            values={'uid': self.uid},
		                            row=('id', self.id))


	def getMainLocation(self) -> Location:
		return self.LocationManager.getLocation(locId=self.locationId)


	def pairingDone(self, uid: str):
		self.uid = uid
		self.DatabaseManager.update(tableName=self.DeviceManager.DB_DEVICE,
		                            callerName=self.DeviceManager.name,
		                            values={'uid': uid},
		                            row=('id', self.id))
		self.MqttManager.publish(constants.TOPIC_DEVICE_UPDATED, payload={'id': self.id, 'type': 'status'})


	def toJson(self) -> str:
		return json.dumps(self.asJson())


	def isInLocation(self, location: Location) -> bool:
		if self.locationId == location.id:
			return True
		for link in self.DeviceManager.getLinksForDevice(device=self):
			if link.locationId == location.id:
				return True
		return False


	def asJson(self):
		return {
			'id'          : self.id,
			'deviceTypeId': self.deviceTypeId,
			'deviceType'  : self.getDeviceType().name,
			'skillName'   : self.skillName,
			'name'        : self.name,
			'uid'         : self.uid,
			'locationId'  : self.locationId,
			'room'        : self.getMainLocation().name,
			'lastContact' : self.lastContact,
			'connected'   : self.connected,
			'display'     : self.display,
			'custom'      : self._customValues
		}


	def changedDevSettingsStructure(self, newSet: dict):
		newSet = newSet.copy()
		for _set in newSet.keys():
			if _set in self.devSettings:
				newSet[_set] = self.devSettings[_set]
		self.devSettings = newSet
		self.saveDevSettings()


	def changeLocation(self, locationId: int):
		self.locationId = locationId
		self.getDeviceType().onChangedLocation(device=self)


	def changeName(self, newName: str):
		self.name = newName
		self.DatabaseManager.update(tableName=self.DeviceManager.DB_DEVICE,
		                            callerName=self.DeviceManager.name,
		                            values={'name': newName},
		                            row=('id', self.id))


	def saveDevSettings(self):
		self.DatabaseManager.update(tableName=self.DeviceManager.DB_DEVICE,
		                            callerName=self.DeviceManager.name,
		                            values={'devSettings': json.dumps(self.devSettings)},
		                            row=('id', self.id))


	def toggle(self):
		return self.getDeviceType().toggle(device=self)


	def getIcon(self):
		return self.getDeviceType().getDeviceIcon(device=self)


	def setCustomValue(self, name: str, value):
		self.customValues[name] = value


	def getCustomValue(self, name: str):
		return self.customValues.get(name, None)


	@property
	def siteId(self) -> str:
		return self.getMainLocation().getSaveName()


	@property
	def display(self) -> dict:
		return self._displaySettings


	@display.setter
	def display(self, value: dict):
		self._displaySettings = value


	@property
	def devSettings(self) -> dict:
		return self._devSettings


	@devSettings.setter
	def devSettings(self, value: dict):
		self._devSettings = value


	@property
	def customValues(self) -> dict:
		return self._customValues


	@customValues.setter
	def customValues(self, value: dict):
		self._customValues = value


	@property
	def location(self) -> str:
		return self.getMainLocation().getSaveName()


	@property
	def skill(self) -> str:
		return self.getDeviceType().skill

