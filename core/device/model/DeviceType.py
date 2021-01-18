import json
import sqlite3
from pathlib import Path
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
		self._allowHeartbeatOverride = data.get('allowHeartbeatOverride', False)

		self._deviceConfigsTemplates = dict()
		self._linkConfigsTemplates = dict()
		self.loadDeviceConfigsTemplates()

		abilities = data.get('abilities', [])
		self._abilities = 0
		for ability in abilities:
			self._abilities |= ability.value


	def loadDeviceConfigsTemplates(self):
		try:
			filepath = Path(f'skills/{self._skillName}/devices/{self._deviceTypeName}.config.template')
			if not filepath.exists():
				return

			data = json.loads(filepath.read_text())

			self._linkConfigsTemplates = data['linkConfigs']
			self._deviceConfigsTemplates = data['deviceConfigs']
		except Exception as e:
			self.logError(f'Error loading device config template for device type **{self._deviceTypeName}** {e}')


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


	def getDeviceTypeIcon(self) -> Path:
		"""
		Return the path of the icon representing this device type
		:return: the icon file path
		"""
		return Path(f'{self.Commons.rootDir()}/skills/{self._skillName}/devices/img/{self._deviceTypeName}.png')


	@property
	def heartbeatRate(self) -> int:
		return self._heartbeatRate


	@property
	def allowHeartbeatOverride(self) -> bool:
		return self._allowHeartbeatOverride


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


	@property
	def skillName(self) -> str:
		return self._skillName


	@property
	def deviceConfigsTemplates(self) -> dict:
		return self._deviceConfigsTemplates


	@property
	def linkConfigsTemplates(self) -> dict:
		return self._linkConfigsTemplates


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


	def toDict(self) -> dict:
		return {
			'deviceTypeName'         : self._deviceTypeName,
			'skillName'              : self._skillName,
			'perLocationLimit'       : self._perLocationLimit,
			'totalDeviceLimit'       : self._totalDeviceLimit,
			'allowLocationLinks'     : self._allowLocationLinks,
			'heartbeatRate'          : self._heartbeatRate,
			'allowHeartbeatOverride' : self._allowHeartbeatOverride,
			'abilities'              : bin(self._abilities),
			'deviceConfigsTemplates' : self._deviceConfigsTemplates,
			'linkConfigsTemplates'   : self._linkConfigsTemplates
		}
