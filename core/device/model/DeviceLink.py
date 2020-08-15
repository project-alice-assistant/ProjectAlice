import ast
import json
import sqlite3
from typing import Union

from core.base.model.ProjectAliceObject import ProjectAliceObject

from dataclasses import dataclass, field

@dataclass
class DeviceLink(ProjectAliceObject):
	data: dict
	
	_id: int = field(init=False)
	_locSettings: dict = field(default_factory=dict)
	_deviceID: int = field(init=False)
	_locationID: int = field(init=False)

	def __post_init__(self):  # NOSONAR
		self._id = self.data['id']
		self._deviceID = self.data['deviceID']
		self._locationID = self.data['locationID']

		if 'locSettings' in self.data.keys() and self.data['locSettings']:
			self._locSettings = ast.literal_eval(self.data['locSettings'])
		else:
			self._locSettings = dict()


	def saveToDB(self):
		values = {'deviceID': self._deviceID, 'locSettings': json.dumps(self._locSettings), 'locationID': self._locationID}
		self._id = self.DatabaseManager.insert(tableName=self.DeviceManager.DB_LINKS,
		                                       values=values,
		                                       callerName=self.DeviceManager.name)
		self.logInfo(f'Created new Link {self._id}')

	def saveLocSettings(self):
		self.DatabaseManager.update(tableName=self.DeviceManager.DB_LINKS,
		                            callerName=self.DeviceManager.name,
		                            values={'locSettings': self.locSettings},
		                            row=('id', self._id))


	def getDevice(self):
		return self.DeviceManager.getDeviceByID(id=self.deviceId)


	def changedLocSettingsStructure(self, newSet: dict):
		newSet = newSet.copy()
		for _set in newSet.keys():
			if _set in self.locSettings:
				newSet[_set] = self.locSettings[_set]
		self.locSettings = newSet
		self.saveLocSettings()


	@property
	def id(self) -> int:
		return self._id


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
			'deviceName'  : self.DeviceManager.getDeviceById(_id=self._deviceID).name,
			'locationID'  : self._locationID,
			'locationName': self.LocationManager.getLocation(locId=self._locationID).name,
			'locSettings' : self._locSettings
		}
