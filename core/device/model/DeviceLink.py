import sqlite3
import ast

from core.base.model.ProjectAliceObject import ProjectAliceObject


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


	def getDevice(self):
		return self.DeviceManager.getDeviceByID(_id=self.deviceId)


	def changedLocSettingsStructure(self, newSet: dict):
		for _set in newSet.keys():
			if _set in self.locSettings:
				newSet[_set] = self.locSettings[_set]
		self._locSettings = newSet
		self.saveToDB()


	@property
	def locSettings(self) -> dict:
		return self._locSettings


	@property
	def locationId(self) -> int:
		return self._locationID


	@property
	def deviceId(self) -> int:
		return self._deviceID
