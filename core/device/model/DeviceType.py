from core.device.model import Device
import sqlite3
from core.base.model.ProjectAliceObject import ProjectAliceObject

class DeviceType(ProjectAliceObject):

	def __init__(self, data: sqlite3.Row, devSettings: dict = {}, locSettings: dict = {}):
		super().__init__()
		self._name = data['name']
		self._skill = data['skill']
		self._skillInstance = None
		self._locationLimit = 0
		self._multiRoom = True
		self._devSettings = devSettings
		self._locSettings = locSettings

		if 'id' in data:
			self._id = data['id']
		else:
			self.saveToDB()

		self.checkChangedSettings()


	def saveToDB(self):
		values = {'skill': self.skill, 'name': self.name, 'locSettings': self._locSettings, 'devSettings': self._devSettings}
		self._id = self.DatabaseManager.insert(tableName=self.DeviceManager.DB_TYPES, values=values, callerName=self.DeviceManager.name)

	def checkChangedSettings(self):
		row = self.DatabaseManager.fetch(tableName=self.DeviceManager.DB_TYPES,
		                                 callerName=self.DeviceManager.name,
		                                 values={'id':self.id})

		if row['devSettings'] != self._devSettings:
			self.DatabaseManager.update(tableName=self.DeviceManager.DB_TYPES,
			                            callerName=self.DeviceManager.name,
			                            values={'devSettings': self._devSettings},
			                            row=('id', values['id']))
			for device in self.DeviceManager.getDevicesByType(deviceType=self.id):
				device.changedDevSettingsStructure(self._devSettings)

		if row['locSettings'] != self._locSettings:
			self.DatabaseManager.update(tableName=self.DeviceManager.DB_TYPES,
			                            callerName=self.DeviceManager.name,
			                            values={'locSettings': self._locSettings},
			                            row=('id', values['id']))
			for links in self.DeviceManager.getDeviceLinksByType(deviceType=self.id):
				links.changedLocSettingsStructure(self._locSettings)



	def canHaveMultipleRooms(self):
		return self._multiRoom


	def getStatusTile(self):
		# Return the tile representing the current status of the device:
		# e.g. a light bulb can be on or off and display its status
		pass


	def getDeviceConfig(self):
		# return the custom configuration of that deviceType
		pass


	def findNewDevice(self, siteId: str):
		# look for new Devices
		pass


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
	def locationLimit(self) -> str:
		return self._locationLimit


	def __repr__(self):
		return f'{self.skill} - {self.name}'
