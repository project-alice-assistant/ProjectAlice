import time
from typing import Iterable

from core.base.model.Manager import Manager
from core.myHome.model.Location import Location
from core.util.model.TelemetryType import TelemetryType
from core.util.model.TelemetryData import TelemetryData


class TelemetryManager(Manager):

	DATABASE = {
		'telemetry': [
			'id integer PRIMARY KEY',
			'type TEXT NOT NULL',
			'value TEXT NOT NULL',
			'service TEXT NOT NULL',
			'siteId TEXT NOT NULL',
			'locationID INTEGER NOT NULL',
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
		self._currentValues = list()


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

		self._currentValues = [ TelemetryData(val) for val in self.getDistinct()]


	# noinspection SqlResolve
	def storeData(self, ttype: TelemetryType, value: str, service: str, siteId: str, timestamp=None, locationID: int = None):
		if not self.isActive:
			return

		timestamp = timestamp or time.time()

		self.databaseInsert(
			tableName='telemetry',
			query='INSERT INTO :__table__ (type, value, service, device, timestamp, locationID) VALUES (:type, :value, :service, :device, :timestamp, :locationID)',
			values={'type': ttype.value, 'value': value, 'service': service, 'device': siteId, 'timestamp': round(timestamp), 'locationID': locationID}
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


	def getData(self, ttype: TelemetryType = None, siteId: str = None, service: str = None, locationId: int = None, historyFrom: int = None, historyTo: int = None, all: bool = False) -> Iterable:
		values = {}
		if ttype:
			values['type'] = ttype
		if locationId:
			values['locationId'] = locationId
		if siteId:
			values['device'] = siteId

		if service:
			values['service'] = service

		dynWhere = [f'{col} = :{col}' for col in values.keys()]


		if historyTo:
			dynWhere.append(f'timestamp <= {historyTo}')
		if historyFrom:
			dynWhere.append(f'timestamp >= {historyFrom}')

		# noinspection SqlResolve
		query = f'SELECT * FROM :__table__ WHERE {" and ".join(dynWhere)} ORDER BY `timestamp` DESC{" LIMIT 1" if not historyFrom and not historyTo and not all else ""}'

		# noinspection SqlResolve
		return self.databaseFetch(
			tableName='telemetry',
			query=query,
			values=values,
			method='all'
		)

	def getDistinct(self, ttype: TelemetryType = None, siteId: str = None, service: str = None, locationId: int = None) -> Iterable:
		values = {}
		group = []
		if ttype:
			values['type'] = ttype
		if locationId:
			values['locationId'] = locationId
		if siteId:
			values['device'] = siteId
		if service:
			values['service'] = service

		where = " WHERE " + " and ".join([f'{col} = :{col}' for col in values.keys()]) if values else ""

		# noinspection SqlResolve
		query = f'SELECT t1.* FROM :__table__ t1 ' \
		        f'INNER JOIN ' \
		        f'(SELECT max(id) id, service, siteId, locationId, type ' \
				f'FROM :__table__ { where } ' \
		        f'GROUP BY `service`, `siteId`, `locationId`, `type`) t2 ' \
		        f'ON t1.id  = t2.id ' \
		        f'ORDER BY `timestamp` DESC '

		# noinspection SqlResolve
		return self.databaseFetch(
			tableName='telemetry',
			query=query,
			values=values,
			method='all'
		)

	def getAllCombinationsForAPI(self):
		return [ val.forApi() for val in self._currentValues ]
