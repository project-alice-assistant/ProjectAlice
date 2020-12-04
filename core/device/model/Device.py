import ast
import json

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.myHome.model.Location import Location


class Device(ProjectAliceObject):

	def __init__(self, data):
		super().__init__()

		self.data: dict = data
		self.connected: bool = False

		self.id: int = self.data['id']
		self.deviceTypeID: int = self.data['typeID']
		self.locationID = self.data['locationID'] if self.data['locationID'] else 0
		self.uid: str = self.data['uid']

		self.name = self.data['name'] if 'name' in self.data.keys() else ''

		self.skillName = self.data['skillName'] if 'skillName' in self.data.keys() else ''

		self._display = ast.literal_eval(self.data['display']) if 'display' in self.data.keys() and self.data['display'] else dict()
		self._devSettings = ast.literal_eval(self.data['devSettings']) if 'devSettings' in self.data.keys() and self.data['devSettings'] else dict()
		self._customValues = ast.literal_eval(self.data['customValues']) if 'customValues' in self.data.keys() and self.data['customValues'] else dict()

		self.lastContact: int = 0


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
			'skillName'   : self.skillName,
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
		return f'Device({self.id} - {self.name}, UID({self.uid}), Location({self.locationID}))'

	def __eq__(self, other):
		return other and self.id == other.id
