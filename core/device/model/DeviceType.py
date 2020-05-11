from core.device.model import Device
import sqlite3
from core.base.model.ProjectAliceObject import ProjectAliceObject

class DeviceType(ProjectAliceObject):

	def __init__(self, data: sqlite3.Row):
		super().__init__()
		self._name = data['name']
		self._parent = data['parent']
		self._skillInstance = None
		self._id = 0

	def saveToDB(self):
		values = {'parent': self.parent, 'name': self.name}
		self._id = self.DatabaseManager.insert(tableName='deviceTypes', query='INSERT INTO :__table__ (parent, name) VALUES (:parent, :name)', values=values, callerName=self.SkillManager.name)


	def getStatusTile(self):
		# Return the tile representing the current status of the device:
		# e.g. a light bulb can be on or off and display its status
		pass

	def getDeviceConfig(self):
		# return the custom configuration of that deviceType
		pass

	def getLinkedRooms(self):
		# return a list of all rooms this device corresponds to
		pass

	def findNewDevice(self, siteId: str):
		# look for new Devices
		pass

	def setParentSkillInstance(self, skill):
		self._skillInstance = skill


	@property
	def parent(self) -> str:
		return self._parent


	@parent.setter
	def parent(self, value: str):
		self._parent = value


	@property
	def name(self) -> str:
		return self._name


	@name.setter
	def name(self, value: str):
		self._name = value


	def __repr__(self):
		return f'{self.parent} - {self.name}'
