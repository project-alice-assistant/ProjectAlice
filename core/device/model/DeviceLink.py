from core.device.model import Device
import sqlite3
from core.base.model.ProjectAliceObject import ProjectAliceObject
import ast

class DeviceLink(ProjectAliceObject):

	def __init__(self, data: sqlite3.Row):
		super().__init__()
		self._locSettings = ast.literal_eval(data['locSettings'])
		self._deviceID = data['deviceID']
		self._locationID = data['locationID']

		if 'id' in data:
			self._id = data['id']
		else:
			self.saveToDB()

	def saveToDB(self):
		values = {'deviceID': self._deviceID, 'locSettings': self._locSettings, 'locationID': self._locationID}
		self._id = self.DatabaseManager.insert(tableName=self.DeviceManager.DB_LINKS, values=values, callerName=self.DeviceManager.name)

	def changedLocSettingsStructure(self, newSet: dict):
		for set in newSet.keys():
			if set in self.locSettings:
				newSet[set] = self.locSettings[set]
		self.locSettings = newSet
		self.saveDevSettings()

	@property
	def locSettings(self) -> dict:
		return self._locSettings
