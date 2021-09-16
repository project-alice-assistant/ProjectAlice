#  Copyright (c) 2021
#
#  This file, TelemetryData.py, is part of Project Alice.
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

from dataclasses import dataclass, field

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.util.model.TelemetryType import TelemetryType


@dataclass
class TelemetryData(ProjectAliceObject):
	"""Class holding one data point of telemetry"""
	data: dict
	service: str = field(init=False)
	deviceId: str = field(init=False)
	locationId: int = field(init=False)
	value: str = field(init=False)
	timestamp: str= field(init=False)
	type: TelemetryType = field(init=False)


	def __post_init__(self):  # NOSONAR
		self.service = self.data['service']
		self.deviceId = self.data['deviceId']
		self.locationId = self.data['locationId']
		self.value = self.data['value']
		self.timestamp = self.data['timestamp']
		self.type = TelemetryType(self.data['type'])


	def forApi(self):
		try:
			return {
				"service"   : self.service,
				"deviceId"  : self.deviceId,
				"device"    : self.getDeviceName(),
				"locationId": self.locationId,
				"location"  : self.getLocationName(),
				"value"     : self.value,
				"timestamp" : self.timestamp,
				"type"      : self.type.value
			}
		except AttributeError:
			return None


	def getDeviceName(self):
		return self.DeviceManager.getDevice(deviceId=int(self.deviceId)).displayName


	def getLocationName(self):
		return self.LocationManager.getLocation(locId=self.locationId).name
