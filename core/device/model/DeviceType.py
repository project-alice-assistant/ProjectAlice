import json
import sqlite3
from typing import Dict, List, Union

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.device.model import Device
from core.device.model.DeviceAbility import DeviceAbility
from core.dialog.model.DialogSession import DialogSession


class DeviceType(ProjectAliceObject):

	def __init__(self, data: Union[Dict, sqlite3.Row]):
		super().__init__()

		if isinstance(data, sqlite3.Row):
			data = self.Commons.dictFromRow(data)

		self._deviceTypeName = data['deviceTypeName']
		self._skillName = data['skillName']
		self._perLocationLimit = data.get('perLocationLimit', 0)
		self._totalDeviceLimit = data.get('totalDeviceLimit', 0)
		self._allowLocationLinks = data.get('allowLocationLinks', True)
		self._heartbeatRate = data.get('heartbeatRate', 5)

		abilities = data.get('abilities', [])
		self._abilities = 0
		for ability in abilities:
			self._abilities |= ability.value


	def hasAbilities(self, abilities: List[DeviceAbility]) -> bool:
		"""
		Checks if that device type has the given abilities, through a bitwise comparison
		:param abilities: a list of DeviceAbility
		:return: boolean
		"""
		check = 0
		for ability in abilities:
			check |= ability.value

		return self._abilities & check == check


	@property
	def heartbeatRate(self) -> int:
		return self._heartbeatRate


	@property
	def abilities(self) -> bin:
		return self._abilities


	@property
	def deviceTypeName(self) -> str:
		return self._deviceTypeName


	@deviceTypeName.setter
	def deviceTypeName(self, value: str):
		self._deviceTypeName = value


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
		return f'{self._skillName} - {self._deviceTypeName}'


	def discover(self, device: Device, uid: str, replyOnDevice: str = '', session: DialogSession = None) -> bool:
		# TODO generic method
		"""
		Method that starts the search for a new device
		:param device: The device class we want to add
		:param uid:
		:param replyOnDevice:
		:param session:
		:return:
		"""
		pass










### to reimplement for any device type






	def getDeviceConfig(self):
		# Getting device config
		pass


	def onChangedLocation(self, device: Device):
		# Location has changed:
		# inform device?
		# change configs?
		pass


### Can be overwritten if required
	def onRename(self, device: Device, newName: str) -> bool:
		# return false if the renaming was not possible
		return True


### Generic part
	@property
	def initialLocationSettings(self) -> Dict:
		return self._locationSettings


	def checkChangedSettings(self):
		return
		# noinspection SqlResolve
		row = self.DeviceManager.databaseFetch(tableName=self.DeviceManager.DB_TYPES,
									            query='SELECT * FROM :__table__ WHERE id = :id',
			                                    values={'id':self.id},
		                                        method='one')

		if row['devSettings'] != json.dumps(self._deviceSettings):
			self.logInfo(f'Updating device Settings structure for {self.name}')
			self.DatabaseManager.update(tableName=self.DeviceManager.DB_TYPES,
			                            callerName=self.DeviceManager.name,
			                            values={'devSettings': json.dumps(self._deviceSettings)},
			                            row=('id', self.id))
			for device in self.DeviceManager.getDevicesByTypeID(deviceTypeID=self.id):
				device.changedDevSettingsStructure(self._deviceSettings)

		if row['locSettings'] != json.dumps(self._locationSettings):
			self.logInfo(f'Updating locations Settings structure for {self.name}')
			self.DatabaseManager.update(tableName=self.DeviceManager.DB_TYPES,
			                            callerName=self.DeviceManager.name,
			                            values={'locSettings': json.dumps(self._locationSettings)},
			                            row=('id', self.id))
			for links in self.DeviceManager.getDeviceLinksByType(deviceType=self.id):
				links.changedLocSettingsStructure(self._locationSettings)


	def checkDevices(self):
		if not self.parentSkillInstance:
			self.logInfo(f'no parent skill!')
			return
		self.DatabaseManager.update(tableName=self.DeviceManager.DB_DEVICE,
		                            callerName=self.DeviceManager.name,
		                            values={'skillName': self.parentSkillInstance.name},
		                            row=('typeID', self.id))


	@property
	def skill(self) -> str:
		return self._skillName


	@skill.setter
	def skill(self, value: str):
		self._skillName = value


	@property
	def id(self) -> str:
		return self._id






