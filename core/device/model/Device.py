import ast
import json
from dataclasses import dataclass, field

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.device.model.Location import Location


@dataclass
class Device(ProjectAliceObject):
	data: dict
	connected: bool = False
	name: str = ''
	lastContact: int = 0
	locationID: int = 0

	id: int = field(init=False)
	deviceTypeID: int = field(init=False)
	uid: str = field(init=False)
	_display: dict = field(default_factory=dict)
	_devSettings: dict = field(default_factory=dict)
	_customValues: dict = field(default_factory=dict)


	def __post_init__(self):  # NOSONAR
		self.id = self.data['id']
		self.deviceTypeID = self.data['typeID']

		self.uid = self.data['uid']
		self.locationID = self.data['locationID']
		if 'display' in self.data.keys() and self.data['display']:
			self._display = ast.literal_eval(self.data['display'])
		else:
			self._display = dict()

		if 'devSettings' in self.data.keys() and self.data['devSettings']:
			self._devSettings = ast.literal_eval(self.data['devSettings'])
		else:
			self._devSettings = dict()

		if 'customValues' in self.data.keys() and self.data['customValues']:
			self._customValues = ast.literal_eval(self.data['customValues'])
		else:
			self._customValues = dict()


	def replace(self, needle: str, haystack: str) -> str:
		return self.name.replace(needle, haystack)


	def clearUID(self):
		self.uid = ''
		self.DatabaseManager.update(tableName=self.DeviceManager.DB_DEVICE,
		                            callerName=self.DeviceManager.name,
		                            values={'uid': self.uid},
		                            row=('id', self.id))


	def getMainLocation(self) -> Location:
		return self.LocationManager.getLocation(locId=self.locationID)


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
		return self.DeviceManager.getDeviceType(_id=self.deviceTypeID)


	def isInLocation(self, location: Location) -> bool:
		if self.locationID == location.id:
			return True
		for link in self.DeviceManager.getLinksForDevice(device=self):
			if link.locationId == location.id:
				return True
		return False


	def asJson(self):
		return {
			'id'          : self.id,
			'deviceTypeID': self.deviceTypeID,
			'deviceType'  : self.getDeviceType().name,
			'skill'       : self.getDeviceType().skill,
			'name'        : self.name,
			'uid'         : self.uid,
			'locationID'  : self.locationID,
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
		self.locationID = locationId
		self.getDeviceType().onChangedLocation(device=self)


	def saveDevSettings(self):
		self.DatabaseManager.update(tableName=self.DeviceManager.DB_DEVICE,
		                            callerName=self.DeviceManager.name,
		                            values={'devSettings': self.devSettings},
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
