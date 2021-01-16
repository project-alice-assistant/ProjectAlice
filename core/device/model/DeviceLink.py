import json
import sqlite3
from typing import Dict, Optional, Union

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.device.model.Device import Device


class DeviceLink(ProjectAliceObject):

	def __init__(self, data: Union[sqlite3.Row, Dict]):
		super().__init__()

		if isinstance(data, sqlite3.Row):
			data = self.Commons.dictFromRow(data)

		self._id: int = data.get('id', -1)
		self._deviceId: int = data.get('deviceId')
		self._targetLocation: int = data.get('targetLocation')

		try:
			self._settings: Dict = json.loads(data.get('settings', '{}'))
		except:
			self._settings = dict()

		if self._id == -1:
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
				query='REPLACE INTO :__table__ (id, deviceId, targetLocation, settings) VALUES (:id, :deviceId, :targetLocation, :settings)',
				callerName=self.DeviceManager.name,
				values={
					'id'            : self._id,
					'deviceId'      : self._deviceId,
					'targetLocation': self._targetLocation,
					'settings'      : json.dumps(self._settings)
				}
			)
		else:
			linkId = self.DatabaseManager.insert(
				tableName=self.DeviceManager.DB_LINKS,
				callerName=self.DeviceManager.name,
				values={
					'deviceId'      : self._deviceId,
					'targetLocation': self._targetLocation,
					'settings'      : json.dumps(self._settings)
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


	@property
	def device(self) -> Optional[Device]:
		return self.DeviceManager.getDevice(deviceId=self._deviceId)


	def toDict(self):
		return {
			'id'            : self._id,
			'deviceId'      : self._deviceId,
			'deviceUid'     : self.deviceUid,
			'targetLocation': self._targetLocation,
			'settings'      : self._settings
		}
