from dataclasses import dataclass, field
from core.util.model.TelemetryType import TelemetryType
from core.base.model.ProjectAliceObject import ProjectAliceObject

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
		return {
			"service": self.service,
			"deviceId": self.deviceId,
			"device": self.getDeviceName(),
			"locationId": self.locationId,
			"location": self.getLocationName(),
			"value": self.value,
			"timestamp": self.timestamp,
			"type": self.type.value
		}

	def getDeviceName(self):
		return self.DeviceManager.getDevice(deviceId=int(self.deviceId)).displayName

	def getLocationName(self):
		return self.LocationManager.getLocation(locId=self.locationId).name
