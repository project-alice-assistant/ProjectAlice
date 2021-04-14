#  Copyright (c) 2021
#
#  This file, DeviceLink.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:46 CEST

import json
import sqlite3
from typing import Dict, Optional, Union, Any

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.device.model.Device import Device
from core.device.model.DeviceType import DeviceType


class DeviceLink(ProjectAliceObject):

	def __init__(self, data: Union[sqlite3.Row, Dict]):
		super().__init__()
		self._invalid = True

		if isinstance(data, sqlite3.Row):
			data = self.Commons.dictFromRow(data)

		self._id: int = data.get('id', -1)
		self._deviceId: int = data.get('deviceId')
		device: Device = self.DeviceManager.getDevice(deviceId=self._deviceId)
		if not device:
			return

		self._deviceType: DeviceType = device.deviceType
		self._targetLocation: int = data.get('targetLocation')

		try:
			self._configs: Dict = json.loads(data.get('configs', '{}'))
		except:
			self._configs = dict()

		if self._id == -1:
			self.saveToDB()

		self._invalid = False


	@property
	def invalid(self) -> bool:
		return self._invalid


	@invalid.setter
	def invalid(self, value: bool):
		self._invalid = value


	def _loadConfigs(self):
		templates = self._deviceType.linkConfigsTemplates
		changes = False
		for configName, configData in templates.items():
			if configName not in self._configs:
				self._configs[configName] = configData['defaultValue']
				changes = True

		for configName, configValue in self._configs.copy().items():
			if configName not in templates:
				self._configs.pop(configName, None)
				continue

			definition = templates[configName]
			if definition['dataType'] != 'list' and definition['dataType'] != 'longstring' and 'onInit' not in definition:
				if not isinstance(configValue, type(definition['defaultValue'])):
					changes = True
					try:
						# First try to cast the setting we have to the new type
						self._configs[configName] = type(definition['defaultValue'])(configValue)
					except Exception:
						# If casting failed let's fall back to the new default value
						self._configs[configName] = definition['defaultValue']
			elif definition['dataType'] == 'list' and 'onInit' not in definition:
				values = definition['values'].values() if isinstance(definition['values'], dict) else definition['values']

				if self._configs[configName] and self._configs[configName] not in values:
					changes = True
					self._configs[configName] = definition['defaultValue']

		if changes:
			self.saveToDB()


	# noinspection SqlResolve
	def saveToDB(self):
		"""
		Updates or inserts this link in DB
		:return:
		"""
		if self._id != -1:
			self.DatabaseManager.replace(
				tableName=self.DeviceManager.DB_LINKS,
				query='REPLACE INTO :__table__ (id, deviceId, targetLocation, configs) VALUES (:id, :deviceId, :targetLocation, :configs)',
				callerName=self.DeviceManager.name,
				values={
					'id'            : self._id,
					'deviceId'      : self._deviceId,
					'targetLocation': self._targetLocation,
					'configs'       : json.dumps(self._configs)
				}
			)
		else:
			linkId = self.DatabaseManager.insert(
				tableName=self.DeviceManager.DB_LINKS,
				callerName=self.DeviceManager.name,
				values={
					'deviceId'      : self._deviceId,
					'targetLocation': self._targetLocation,
					'configs'       : json.dumps(self._configs)
				}
			)

			self._id = linkId


	@property
	def id(self) -> int:
		return self._id


	@property
	def deviceId(self) -> int:
		return self._deviceId


	@property
	def deviceUid(self) -> str:
		device = self.DeviceManager.getDevice(deviceId=self._deviceId)
		return device.uid if device else '-1'


	@property
	def targetLocation(self) -> int:
		return self._targetLocation


	@targetLocation.setter
	def targetLocation(self, newTarget: int):
		self._targetLocation =  newTarget


	@property
	def device(self) -> Optional[Device]:
		return self.DeviceManager.getDevice(deviceId=self._deviceId)


	def updateConfigs(self, configs: dict):
		self._configs = {**self._configs, **configs}


	def getConfig(self, key: str, default: Any = False) -> Any:
		return self._configs.get(key, default)


	def toDict(self):
		return {
			'id'            : self._id,
			'deviceId'      : self._deviceId,
			'deviceUid'     : self.deviceUid,
			'targetLocation': self._targetLocation,
			'configs'       : self._configs
		}
