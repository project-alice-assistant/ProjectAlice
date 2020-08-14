import ast
import json
import sqlite3
from typing import Union

from core.base.model.ProjectAliceObject import ProjectAliceObject


class DeviceLink(ProjectAliceObject):

	def __init__(self, data: Union[dict, sqlite3.Row]):
		super().__init__()
		self._locSettings = dict()
		if 'locSettings' in data and data['locSettings']:
			self._locSettings = ast.literal_eval(data['locSettings'])
		self._deviceID = data['deviceID']
		self._locationID = data['locationID']

		if 'id' in data:
			self._id = data['id']
		else:
			self.saveToDB()


	@property
	def id(self) -> int:
		return self._id


	def saveToDB(self):
		values = {'deviceID': self._deviceID, 'locSettings': json.dumps(self._locSettings), 'locationID': self._locationID}
		self._id = self.DatabaseManager.insert(tableName=self.DeviceManager.DB_LINKS,
		                                       values=values,
		                                       callerName=self.DeviceManager.name)

	def saveLocSettings(self):
		self.DatabaseManager.update(tableName=self.DeviceManager.DB_LINKS,
		                            callerName=self.DeviceManager.name,
		                            values={'locSettings': self.locSettings},
		                            row=('id', self._id))


	def getDevice(self):
		return self.DeviceManager.getDeviceByID(_id=self.deviceId)


	def changedLocSettingsStructure(self, newSet: dict):
		newSet = newSet.copy()
		for _set in newSet.keys():
			if _set in self.locSettings:
				newSet[_set] = self.locSettings[_set]
		self.locSettings = newSet
		self.saveLocSettings()


	@property
	def locSettings(self) -> dict:
		return self._locSettings


	@locSettings.setter
	def locSettings(self, locSettings):
		self._locSettings = locSettings


	@property
	def locationId(self) -> int:
		return self._locationID


	@property
	def deviceId(self) -> int:
		return self._deviceID

	def asJson(self):
		return {
			'id'          : self._id,
			'deviceID'    : self._deviceID,
			'locationID'  : self._locationID,
			'locSettings' : self._locSettings
		}
