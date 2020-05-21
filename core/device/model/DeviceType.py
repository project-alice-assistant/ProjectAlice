from core.device.model import Device
import sqlite3
from core.base.model.ProjectAliceObject import ProjectAliceObject

class DeviceType(ProjectAliceObject):

	def __init__(self, data: sqlite3.Row, devSettings: dict = {}, locSettings: dict = {}, multiRoom: bool = True, locationLimit: int = 0, deviceLimit: int = 0):
		super().__init__()
		self._name = data['name']
		self._skill = data['skill']
		self._skillInstance = None
		self._locationLimit = locationLimit
		self._deviceLimit = deviceLimit
		self._multiRoom = multiRoom
		self._devSettings = devSettings
		self._locSettings = locSettings

		if 'id' in data:
			self._id = data['id']
		else:
			self.saveToDB()

		self.checkChangedSettings()


### to reimplement for any device type
### Find A new Device
	def discover(self, uid: str = None, device: Device = None):
		# implement the method which can start the search for a new device.
		# on success the uid should be added to the device and it should be saved
		# for this, call device.pairingDone(uid)
		pass


	def getStatusTile(self):
		# Return the tile representing the current status of the device:
		# e.g. a light bulb can be on or off and display its status
		pass

### Generic part
	def saveToDB(self):
		values = {'skill': self.skill, 'name': self.name, 'locSettings': self._locSettings, 'devSettings': self._devSettings}
		self._id = self.DatabaseManager.insert(tableName=self.DeviceManager.DB_TYPES, values=values, callerName=self.DeviceManager.name)

	def checkChangedSettings(self):
		row = self.DeviceManager.databaseFetch(tableName=self.DeviceManager.DB_TYPES,
			                                    values={'id':self.id})

		if row['devSettings'] != self._devSettings:
			self.DatabaseManager.update(tableName=self.DeviceManager.DB_TYPES,
			                            callerName=self.DeviceManager.name,
			                            values={'devSettings': self._devSettings},
			                            row=('id', self.id))
			for device in self.DeviceManager.getDevicesByType(deviceType=self.id):
				device.changedDevSettingsStructure(self._devSettings)

		if row['locSettings'] != self._locSettings:
			self.DatabaseManager.update(tableName=self.DeviceManager.DB_TYPES,
			                            callerName=self.DeviceManager.name,
			                            values={'locSettings': self._locSettings},
			                            row=('id', self.id))
			for links in self.DeviceManager.getDeviceLinksByType(deviceType=self.id):
				links.changedLocSettingsStructure(self._locSettings)


	def setParentSkillInstance(self, skill):
		self._skillInstance = skill


	@property
	def skill(self) -> str:
		return self._skill


	@skill.setter
	def skill(self, value: str):
		self._skill = value


	@property
	def id(self) -> str:
		return self._id


	@property
	def name(self) -> str:
		return self._name


	@name.setter
	def name(self, value: str):
		self._name = value


	@property
	def locationLimit(self) -> int:
		return self._locationLimit


	@property
	def deviceLimit(self) -> int:
		return self._locationLimit


	@property
	def multiRoom(self) -> bool:
		return self._multiRoom


	def __repr__(self):
		return f'{self.skill} - {self.name}'
