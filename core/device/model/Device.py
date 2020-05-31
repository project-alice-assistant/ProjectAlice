import json
from dataclasses import dataclass, field
from core.device.model.DeviceType import DeviceType
from core.device.model.Location import Location
from core.base.model.ProjectAliceObject import ProjectAliceObject
import ast

@dataclass
class Device(ProjectAliceObject):
	data: dict
	connected: bool = False
	name: str = ''
	lastContact: int = 0

	id: int = field(init=False)
	deviceTypeID: int = field(init=False)
	uid: str = field(init=False)


	def __post_init__(self): #NOSONAR
		self.id = self.data['id']
		self.deviceTypeID = self.data['typeID']

		self.uid = self.data['uid']
		self.locationID = self.data['locationID']
		if self.data['display']:
			self._display = ast.literal_eval(self.data['display'])
		else:
			self._display = {}

		if 'devSettings' in self.data:
			self._devSettings = ast.literal_eval(self.data['devSettings'])
		else:
			self._devSettings = dict()

		if 'customValues' in self.data:
			self._customValues = ast.literal_eval(self.data['customValues'])
		else:
			self._customValues = dict()


	def getMainLocation(self) -> Location:
		return self.LocationManager.getLocation(id=self.locationID)


	def pairingDone(self, uid: str):
		self.uid = uid
		self.DatabaseManager.update(tableName=self.DeviceManager.DB_DEVICE,
		                            callerName=self.DeviceManager.name,
		                            values={'uid': uid},
		                            row=('id',self.id))
		# todo broadcast: pairing done


	def toJson(self) -> str:
		return json.dumps(self.asJson())


	def getDeviceType(self) -> DeviceType:
		return self.DeviceManager.getDeviceType(id=self.deviceTypeID)


	def isInLocation(self, location: Location) -> bool:
		if self.locationID == location.id:
			return True
		# todo check links


	def asJson(self):
		return {
			'id': self.id,
			'deviceTypeID': self.deviceTypeID,
			'deviceType': self.getDeviceType().name,
			'skill': self.getDeviceType().skill,
			'name': self.name,
			'uid': self.uid,
			'locationID': self.locationID,
			'room': self.getMainLocation().name,
			'lastContact': self.lastContact,
			'connected': self.connected,
			'display': self.display
		}


	def changedDevSettingsStructure(self, newSet: dict):
		self.logInfo(newSet)
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


	def toggle(self):
		self.getDeviceType().toggle(device=self)


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
	def deviceType(self) -> DeviceType:
		return self.getDeviceType()

	@property
	def room(self) -> str:
		return self.getMainLocation().getSaveName()

	@property
	def skill(self) -> str:
		return self.getDeviceType().skill
