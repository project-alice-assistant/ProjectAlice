import json
from dataclasses import dataclass, field
from core.device.model import DeviceType
from core.base.model.ProjectAliceObject import ProjectAliceObject

@dataclass
class Device(ProjectAliceObject):
	data: dict
	connected: bool = False
	name: str = ''
	lastContact: int = 0

	id: int = field(init=False)
	deviceTypeID: str = field(init=False)
	uid: str = field(init=False)
	room: str = field(init=False)

	def __post_init__(self): #NOSONAR
		self.id = self.data['id']
		self.deviceTypeID = self.data['typeID']

		self.uid = self.data['uid']
		self.locationID = self.data['locationID']
		if self.data['display']:
			self._display = self.data['display']
		else:
			self._display = {}

		if 'devSettings' in self.data:
			self._devSettings = data['devSettings']
		else:
			self._devSettings = dict()


	def toJson(self) -> str:
		return json.dumps(self.asJson())

	def getDeviceType(self) -> DeviceType:
		return self.DeviceManager.getDeviceType(id=self.deviceTypeID)

	def asJson(self):
		return {
			'id': self.id,
			'deviceTypeID': self.deviceTypeID,
			'deviceType': self.getDeviceType().name,
			'skill': self.getDeviceType().skill,
			'name': self.name,
			'uid': self.uid,
			'locationID': self.locationID,
			'lastContact': self.lastContact,
			'connected': self.connected,
			'display': self.display
		}


	def changedDevSettingsStructure(self, newSet: dict):
		for set in newSet.keys():
			if set in self.devSettings:
				newSet[set] = self.devSettings[set]
		self.devSettings = newSet
		self.saveDevSettings()


	def saveDevSettings(self):
		self.DatabaseManager.update(tableName=self.DeviceManager.DB_DEVICE,
		                            callerName=self.DeviceManager.name,
		                            values={'devSettings': self.devSettings},
		                            row=('id',self.id))


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
