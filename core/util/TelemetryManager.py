import time
from typing import Iterable

from core.base.model.Manager import Manager
from core.util.model.TelemetryType import TelemetryType


class TelemetryManager(Manager):

	DATABASE = {
		'telemetry': [
			'id integer PRIMARY KEY',
			'type TEXT NOT NULL',
			'value TEXT NOT NULL',
			'service TEXT NOT NULL',
			'siteId TEXT NOT NULL',
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


	# noinspection SqlResolve
	def loadData(self):
		if not self._isActive:
			return

		self._data = self.databaseFetch(
			tableName='telemetry',
			query='SELECT * FROM :__table__ ORDER BY timestamp DESC LIMIT 200',
			method='all'
		)


	# noinspection SqlResolve
	def storeData(self, ttype: TelemetryType, value: str, service: str, siteId: str, timestamp=None):
		if not self.isActive:
			return

		timestamp = timestamp or time.time()

		self.databaseInsert(
			tableName='telemetry',
			query='INSERT INTO :__table__ (type, value, service, siteId, timestamp) VALUES (:type, :value, :service, :siteId, :timestamp)',
			values={'type': ttype.value, 'value': value, 'service': service, 'siteId': siteId, 'timestamp': round(timestamp)}
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
				self.broadcast(method=message, exceptions=[self.name], propagateToSkills=True, service=service, trigger=settings[0], value=value, threshold=threshold, area=siteId )
				break


	def getData(self, ttype: TelemetryType, siteId: str, service: str = None) -> Iterable:
		values = {'type': ttype.value, 'siteId': siteId}
		if service:
			values['service'] = service

		# noinspection SqlResolve
		return self.databaseFetch(
			tableName='telemetry',
			query="SELECT value, timestamp FROM :__table__ WHERE type = :type and siteId = :siteId ORDER BY `timestamp` DESC LIMIT 1",
			values=values
		)
