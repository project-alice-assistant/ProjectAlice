#  Copyright (c) 2021
#
#  This file, TelemetryManager.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:48 CEST

import time
from typing import List

from core.base.model.Manager import Manager
from core.util.model.TelemetryData import TelemetryData
from core.util.model.TelemetryType import TelemetryType


class TelemetryManager(Manager):

	DATABASE = {
		'telemetry': [
			'id integer PRIMARY KEY',
			'type TEXT NOT NULL',
			'value TEXT NOT NULL',
			'service TEXT NOT NULL',
			'deviceId INTEGER NOT NULL',
			'locationId INTEGER NOT NULL',
			'timestamp INTEGER NOT NULL'
		]
	}

	TELEMETRY_MAPPINGS = {
		TelemetryType.WIND_STRENGTH: {
			'onWindy': ['upperThreshold', 'WindAlertFromKmh']
		},
		TelemetryType.TEMPERATURE: {
			'onTemperatureHighAlert': ['upperThreshold', 'TemperatureAlertHigh'],
			'onTemperatureLowAlert': ['lowerThreshold', 'TemperatureAlertLow'],
			'onFreezing': ['lowerThreshold', 0]
		},
		TelemetryType.CO2: {
			'onCO2Alert': ['upperThreshold', 'CO2AlertHigh']
		},
		TelemetryType.GAS: {
			'onGasAlert': ['upperThreshold', 'GasAlertHigh']
		},
		TelemetryType.HUMIDITY: {
			'onHumidityHighAlert': ['upperThreshold', 'HumidityAlertHigh'],
			'onHumidityLowAlert': ['lowerThreshold', 'HumidityAlertLow']
		},
		TelemetryType.PRESSURE: {
			'onPressureHighAlert': ['upperThreshold', 'PressureAlertHigh'],
			'onPressureLowAlert': ['lowerThreshold', 'PressureAlertLow']
		},
		TelemetryType.NOISE: {
			'onNoiseAlert': ['upperThreshold', 'NoiseAlert']
		},
		TelemetryType.RAIN: {
			'onRaining': None
		},
		TelemetryType.SUM_RAIN_1: {
			'onTooMuchRain': ['upperThreshold', 'TooMuchRainAlert']
		},
		TelemetryType.UV_INDEX: {
			'onUVIndexAlert': ['upperThreshold', 'UVIndexAlert']
		}
	}


	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)
		self._data = list()
		self._currentValues: List[TelemetryData] = list()


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('enableDataStoring'):
			self._isActive = False
			self.logInfo('Data storing is disabled')
		else:
			self.loadData()


	def onQuarterHour(self):
		if self.ConfigManager.getAliceConfigByName('autoPruneStoredData') > 0 and self._isActive:
			self.pruneTable('telemetry')


	def loadData(self):
		if not self._isActive:
			return

		self._currentValues = [TelemetryData(val) for val in self.getDistinct()]


	def currentValue(self, ttype: TelemetryType, value: str, service: str, deviceId: int, timestamp=None, locationId: int = None) -> bool:
		"""
		check currentValue needs new data
		:param ttype:
		:param value:
		:param service:
		:param deviceId:
		:param timestamp:
		:param locationId:
		:return:
		"""
		match = None
		for current in self._currentValues:
			if current.type == ttype and current.service == service and current.deviceId == deviceId and current.locationId == locationId:
				match = current
		if match:
			if match.timestamp == timestamp and match.value == value:
				# skip exact duplicates
				return False
			else:
				match.timestamp = timestamp
				match.value = value
				return True
		else:
			self._currentValues.append(TelemetryData({'type': ttype,
			                                          'value': value,
			                                          'service': service,
			                                          'deviceId': deviceId,
			                                          'timestamp': timestamp,
			                                          'locationId': locationId}))
			return True

	# noinspection SqlResolve
	def storeData(self, ttype: TelemetryType, value: str, service: str, deviceId: int, timestamp=None, locationId: int = None) -> bool:
		"""
		Store telemetry data to the database and the list of current values.
		Duplicates are filtered out.
		If a new entry was added, true is returned, if not false
		:param ttype:
		:param value:
		:param service:
		:param deviceId:
		:param timestamp:
		:param locationId:
		:return bool: if a new entry was created
		"""
		if not self.isActive:
			return False

		timestamp = timestamp or time.time()

		if not self.currentValue(ttype, value, service, deviceId,timestamp, locationId):
			return False

		self.databaseInsert(
			tableName='telemetry',
			query='INSERT INTO :__table__ (type, value, service, deviceId, timestamp, locationId) VALUES (:type, :value, :service, :deviceId, :timestamp, :locationId)',
			values={'type': ttype.value, 'value': value, 'service': service, 'deviceId': deviceId, 'timestamp': round(timestamp), 'locationId': locationId}
		)

		telemetrySkill = self.SkillManager.getSkillInstance('Telemetry')
		messages = self.TELEMETRY_MAPPINGS.get(ttype, dict())
		for message, settings in messages.items():
			if settings is None:
				self.broadcast(method=message, exceptions=[self.name], propagateToSkills=True, service=service)
				break

			if not telemetrySkill:
				continue

			threshold = float(self.ConfigManager.getSkillConfigByName('Telemetry', settings[1]) if isinstance(settings[1], str) else settings[1])
			value = float(value)
			if settings[0] == 'upperThreshold' and value > threshold or \
					settings[0] == 'lowerThreshold' and value < threshold:
				self.broadcast(method=message, exceptions=[self.name], propagateToSkills=True, service=service, trigger=settings[0], value=value, threshold=threshold, area=deviceId )
				break

		return True


	def getData(self, ttype: TelemetryType = None, deviceId: str = None, service: str = None, locationId: int = None, historyFrom: int = None, historyTo: int = None, everything: bool = False) -> List:
		values = dict()
		if ttype:
			values['type'] = ttype
		if locationId:
			values['locationId'] = locationId
		if deviceId:
			values['deviceId'] = deviceId

		if service:
			values['service'] = service

		dynWhere = [f'{col} = :{col}' for col in values.keys()]


		if historyTo:
			dynWhere.append(f'timestamp <= {historyTo}')
		if historyFrom:
			dynWhere.append(f'timestamp >= {historyFrom}')

		# noinspection SqlResolve
		query = f'SELECT * FROM :__table__ WHERE {" and ".join(dynWhere)} ORDER BY `timestamp` DESC{" LIMIT 1" if not historyFrom and not historyTo and not everything else ""}'

		# noinspection SqlResolve
		return self.databaseFetch(
			tableName='telemetry',
			query=query,
			values=values
		)


	def getDistinct(self, ttype: TelemetryType = None, deviceId: str = None, service: str = None, locationId: int = None) -> List:
		values = dict()
		if ttype:
			values['type'] = ttype.value
		if locationId:
			values['locationId'] = locationId
		if deviceId:
			values['deviceId'] = deviceId
		if service:
			values['service'] = service

		where = " WHERE " + " and ".join([f'{col} = :{col}' for col in values.keys()]) if values else ""

		# noinspection SqlResolve
		query = f'SELECT t1.* FROM :__table__ t1 ' \
		        f'INNER JOIN ' \
		        f'(SELECT max(id) id, service, deviceId, locationId, type ' \
				f'FROM :__table__ { where } ' \
		        f'GROUP BY `service`, `deviceId`, `locationId`, `type`) t2 ' \
		        f'ON t1.id  = t2.id ' \
		        f'ORDER BY `timestamp` DESC '

		# noinspection SqlResolve
		return self.databaseFetch(
			tableName='telemetry',
			query=query,
			values=values
		)


	def getAllCombinationsForAPI(self):
		llist = [val.forApi() for val in self._currentValues]
		llist = [l for l in llist if l is not None]  # workaround until obsolete telemetry is purged
		return llist
