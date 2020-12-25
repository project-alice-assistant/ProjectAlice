import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Union

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.device.model.DeviceAbility import DeviceAbility
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
		self._parentLocation: int = data.get('parentLocation', 0)
		self._deviceType: DeviceType = self.DeviceManager.getDeviceType(self._skillName, self._typeName)
		self._abilities: int = -1 if not data.get('abilities', None) else self.setAbilities(data['abilities'])
		self._deviceParams: Dict = json.loads(data.get('deviceParams', '{}'))
		self._displayName: str = data.get('displayName', '')
		self._connected: bool = False

		# Settings are for UI, all the components use the same variable
		self._settings = json.loads(data.get('settings', '{}')) if isinstance(data.get('settings', '{}'), str) else data.get('settings', dict())
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

		if not self._displayName:
			self._displayName = self._typeName

		if self._id == -1:
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
				query='REPLACE INTO :__table__ (id, uid, parentLocation, typeName, skillName, settings, displayName, deviceParams) VALUES (:id, :uid, :parentLocation, :typeName, :skillName, :settings, :displayName, :deviceParams)',
				callerName=self.DeviceManager.name,
				values={
					'id'             : self._id,
					'uid'            : self._uid,
					'parentLocation' : self._parentLocation,
					'typeName'       : self._typeName,
					'skillName'      : self._skillName,
					'settings'       : json.dumps(self._settings),
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
					'parentLocation' : self._parentLocation,
					'typeName'       : self._typeName,
					'skillName'      : self._skillName,
					'settings'       : json.dumps(self._settings),
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
	def parentLocation(self) -> int:
		return self._parentLocation


	@parentLocation.setter
	def parentLocation(self, value: int):
		self._parentLocation = value


	@property
	def skillName(self) -> str:
		return self._skillName


	@property
	def typeName(self) -> str:
		return self._typeName


	@property
	def id(self) -> str:
		#Prefer using uid when possible
		return self._id


	@property
	def uid(self) -> str:
		return self._uid

	@property
	def displayName(self) -> str:
		return self._displayName


	@displayName.setter
	def displayName(self, value: str):
		self._displayName = value


	def toDict(self) -> dict:
		return {
			'abilities'      : bin(self.getAbilities()),
			'connected'      : self._connected,
			'deviceParams'   : self._deviceParams,
			'displayName'    : self._displayName,
			'settings'       : self._settings,
			'id'             : self._id,
			'lastContact'    : self._lastContact,
			'parentLocation' : self._parentLocation,
			'skillName'      : self._skillName,
			'typeName'       : self._typeName,
			'uid'            : self._uid
		}


	def getDeviceIcon(self) -> Path:
		"""
		Return the path of the icon representing the current status of the device
		e.g. a light bulb can be on or off and display its status
		:return: the icon file path
		"""
		return Path(f'{self.Commons.rootDir()}/skills/{self.skillName}/device/img/{self.typeName}.png')


	def updateSettings(self, settings: dict):
		self._settings = {**self._settings, **settings}


	def getParam(self, key: str, default: Any = False) -> Any:
		return self._deviceParams.get(key, default)


	def updateParams(self, key: str, value: Any):
		self._deviceParams[key] = value
		self.saveToDB()


	def onUIClick(self):
		pass # Implemented by child


	def __repr__(self):
		return f'Device({self._id} - {self._displayName}, uid({self._uid}), Location({self._parentLocation}))'


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
		if self.deviceType.onRename(device=self, newName=newName):
			self.DatabaseManager.update(tableName=self.DeviceManager.DB_DEVICE,
			                            callerName=self.DeviceManager.name,
			                            values={'name': newName},
			                            row=('id', self.id))
		else:
			raise Exception('renaming failed')


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
		return self._settings


	@display.setter
	def display(self, value: dict):
		self._settings = value


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

