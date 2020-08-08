import json
import sqlite3
from typing import Dict

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.device.model import Device
from core.dialog.model.DialogSession import DialogSession


class DeviceType(ProjectAliceObject):

	DEV_SETTINGS = dict()
	LOC_SETTINGS = dict()

	def __init__(self, data: sqlite3.Row, devSettings = None, locSettings = None, allowLocationLinks: bool = True, perLocationLimit: int = 0, totalDeviceLimit: int = 0, heartbeatRate: int = 5):
		super().__init__()

		if locSettings is None:
			locSettings = {}
		if devSettings is None:
			devSettings = {}

		self._name = data['name']
		self._skill = data['skill']
		self._skillInstance = None
		self._perLocationLimit = perLocationLimit
		self._totalDeviceLimit = totalDeviceLimit
		self._allowLocationLinks = allowLocationLinks
		self._devSettings = devSettings
		self._locSettings = locSettings
		self.heartbeatRate = heartbeatRate

		if 'id' in data:
			self._id = data['id']
		else:
			self.saveToDB()

		self.checkChangedSettings()


### to reimplement for any device type
	def discover(self, device: Device, uid: str, replyOnSiteId: str = '', session: DialogSession = None) -> bool:
		# implement the method which can start the search for a new device.
		# on success the uid should be added to the device and it should be saved
		# for this, call device.pairingDone(uid)
		# return False if busy
		# if not implemented, it will always look busy!
		raise NotImplementedError


	def getDeviceIcon(self, device: Device) -> str:
		# Return the tile representing the current status of the device:
		# e.g. a light bulb can be on or off and display its status
		raise NotImplementedError


	def toggle(self, device: Device):
		# the functionality to execute when the device is clicked/toggled in the webinterface
		raise NotImplementedError


	def getDeviceConfig(self):
		# Getting device config
		pass


	def onChangedLocation(self, device: Device):
		# Location has changed:
		# inform device?
		# change configs?
		pass


### Generic part
	@property
	def initialLocationSettings(self) -> Dict:
		return self._locSettings


	def saveToDB(self):
		values = {'skill': self.skill, 'name': self.name, 'locSettings': json.dumps(self._locSettings), 'devSettings': json.dumps(self._devSettings)}
		self._id = self.DatabaseManager.insert(tableName=self.DeviceManager.DB_TYPES, values=values, callerName=self.DeviceManager.name)


	def checkChangedSettings(self):
		# noinspection SqlResolve
		row = self.DeviceManager.databaseFetch(tableName=self.DeviceManager.DB_TYPES,
									            query='SELECT * FROM :__table__ WHERE id = :id',
			                                    values={'id':self.id},
		                                        method='one')

		if row['devSettings'] != str(self._devSettings):
			self.logInfo(f'Updating device Settings structure for {self.name}')
			self.DatabaseManager.update(tableName=self.DeviceManager.DB_TYPES,
			                            callerName=self.DeviceManager.name,
			                            values={'devSettings': json.dumps(self._devSettings)},
			                            row=('id', self.id))
			for device in self.DeviceManager.getDevicesByTypeID(deviceTypeID=self.id):
				device.changedDevSettingsStructure(self._devSettings)

		if row['locSettings'] != str(self._locSettings):
			self.logInfo(f'Updating locations Settings structure for {self.name}')
			self.DatabaseManager.update(tableName=self.DeviceManager.DB_TYPES,
			                            callerName=self.DeviceManager.name,
			                            values={'locSettings': json.dumps(self._locSettings)},
			                            row=('id', self.id))
			for links in self.DeviceManager.getDeviceLinksByType(deviceType=self.id):
				links.changedLocSettingsStructure(self._locSettings)


	@property
	def parentSkillInstance(self):
		return self._skillInstance


	@parentSkillInstance.setter
	def parentSkillInstance(self, skill):
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
	def totalDeviceLimit(self) -> int:
		return self._totalDeviceLimit


	@property
	def perLocationLimit(self) -> int:
		return self._perLocationLimit


	@property
	def allowLocationLinks(self) -> bool:
		return self._allowLocationLinks


	def __repr__(self):
		return f'{self.skill} - {self.name}'
