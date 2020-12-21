import json
import sqlite3
from typing import Dict, List, Union

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.device.model.DeviceAbility import DeviceAbility
from core.device.model.DeviceException import DeviceTypeUndefined
from core.myHome.model.Location import Location


class Device(ProjectAliceObject):

	def __init__(self, data: Union[sqlite3.Row, Dict]):
		super().__init__()

		if isinstance(data, sqlite3.Row):
			data = self.Commons.dictFromRow(data)

		self._data: dict = data
		self._connected: bool = False

		self._locationId = data.get('locationId', 0)
		self._name = data.get('name', '')
		self._skillName = data.get('skillName', '')
		self._uid: str = data['uid']

		self._deviceType = self.DeviceManager.getDeviceType(self._skillName, self.name)
		self._abilities = 0 # We can override device's ability from DeviceType in case needed (think main unit with mic and sound disabled)

		if not self._deviceType:
			raise DeviceTypeUndefined(f'{self._skillName}_{self.name}')


		self._display: Dict = json.loads(data.get('display', '{}'))
		self._deviceParams: Dict = json.loads(data.get('deviceParams', '{}'))

		self._lastContact: int = 0


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
		self._abilities = 0
		for ability in abilities:
			self._abilities |= ability.value


	@property
	def connected(self) -> bool:
		return self._connected


	@connected.setter
	def connected(self, value: bool):
		self._connected = value







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


	def getDeviceType(self):
		return self.DeviceManager.getDeviceType(_id=self.deviceTypeId)


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
		return self._display


	@display.setter
	def display(self, value: dict):
		self._display = value


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
	def deviceType(self):
		return self.getDeviceType()


	@property
	def location(self) -> str:
		return self.getMainLocation().getSaveName()


	@property
	def skill(self) -> str:
		return self.getDeviceType().skill


	def __repr__(self):
		return f'Device({self.id} - {self.name}, UId({self.uid}), Location({self.locationId}))'

	def __eq__(self, other):
		return other and self.id == other.id
