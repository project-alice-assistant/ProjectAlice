from dataclasses import dataclass, field
from core.util.model.TelemetryType import TelemetryType
from core.base.model.ProjectAliceObject import ProjectAliceObject

@dataclass
class TelemetryData(ProjectAliceObject):
	"""Class holding one data point of telemetry"""
	data: dict
	service: str = field(init=False)
	siteId: str = field(init=False)
	locationId: int = field(init=False)
	value: str = field(init=False)
	timestamp: str= field(init=False)
	type: TelemetryType = field(init=False)

	def __post_init__(self):  # NOSONAR
		self.service = self.data['service']
		self.siteId = self.data['siteId']
		self.locationId = self.data['locationId']
		self.value = self.data['value']
		self.timestamp = self.data['timestamp']
		self.type = self.data['type']

	def forApi(self):
		return {
			"service": self.service,
			"deviceId": self.siteId,
			"device": self.getDeviceName(),
			"locationId": self.locationId,
			"location": self.getLocationName(),
			"value": self.value,
			"timestamp": self.timestamp,
			"type": self.type
		}

	def getDeviceName(self):
		return self.DeviceManager.getDeviceByUID(self.siteId).name

	def getLocationName(self):
		return self.LocationManager.getLocation(locId=self.locationId).name
