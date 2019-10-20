import time
from typing import Iterable

from core.base.SuperManager import SuperManager
from core.base.model.Manager import Manager
from core.util.model.TelemetryType import TelemetryType


class TelemetryManager(Manager):
	NAME = 'TelemetryManager'

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


	def __init__(self):
		super().__init__(self.NAME, self.DATABASE)
		self._data = list


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
	def storeData(self, ttype: TelemetryType, value: str, service: str, siteId: str, timestamp = None):
		if not self.isActive:
			return

		timestamp = timestamp or time.time()

		self.databaseInsert(
			tableName='telemetry',
			query='INSERT INTO :__table__ (type, value, service, siteId, timestamp) VALUES (:type, :value, :service, :siteId, :timestamp)',
			values={'type': ttype.value, 'value': value, 'service': service, 'siteId': siteId, 'timestamp': round(timestamp)}
		)

		if ttype == TelemetryType.WIND_STRENGTH:
			if float(value) > float(self.ConfigManager.getModuleConfigByName('WindAlertFromKmh')):
				self.broadcast(method='onWindy', exceptions=self.name, propagateToModules=True, args=[service])

		elif ttype == TelemetryType.TEMPERATURE:
			if float(value) > float(self.ConfigManager.getModuleConfigByName('TemperatureAlertHigh')):
				self.broadcast(method='onTemperatureHighAlert', exceptions=self.name, propagateToModules=True, args=[service])
			elif float(value) < float(self.ConfigManager.getModuleConfigByName('TemperatureAlertLow')):
				self.broadcast(method='onTemperatureLowAlert', exceptions=self.name, propagateToModules=True, args=[service])
			elif float(value) < 0:
				self.broadcast(method='onFreezing', exceptions=self.name, propagateToModules=True, args=[service])

		elif ttype == TelemetryType.CO2:
			if float(value) > float(self.ConfigManager.getModuleConfigByName('CO2AlertHigh')):
				self.broadcast(method='onCO2Alert', exceptions=self.name, propagateToModules=True, args=[service])

		elif ttype == TelemetryType.HUMIDITY:
			if float(value) > float(self.ConfigManager.getModuleConfigByName('HumidityAlertHigh')):
				self.broadcast(method='onHumidityHighAlert', exceptions=self.name, propagateToModules=True, args=[service])
			elif float(value) < float(self.ConfigManager.getModuleConfigByName('HumidityAlertLow')):
				self.broadcast(method='onHumidityLowAlert', exceptions=self.name, propagateToModules=True, args=[service])

		elif ttype == TelemetryType.PRESSURE:
			if float(value) > float(self.ConfigManager.getModuleConfigByName('PressureAlertHigh')):
				self.broadcast(method='onPressureHighAlert', exceptions=self.name, propagateToModules=True, args=[service])
			elif float(value) < float(self.ConfigManager.getModuleConfigByName('PressureAlertLow')):
				self.broadcast(method='onPressureLowAlert', exceptions=self.name, propagateToModules=True, args=[service])

		elif ttype == TelemetryType.NOISE:
			if float(value) > float(self.ConfigManager.getModuleConfigByName('NoiseAlert')):
				self.broadcast(method='onNoiseAlert', exceptions=self.name, propagateToModules=True, args=[service])

		elif ttype == TelemetryType.RAIN:
			self.broadcast(method='onRaining', exceptions=self.name, propagateToModules=True, args=[service])

		elif ttype == TelemetryType.SUM_RAIN_1:
			if float(value) > float(self.ConfigManager.getModuleConfigByName('TooMuchRainAlert')):
				self.broadcast(method='onTooMuchRain', exceptions=self.name, propagateToModules=True, args=[service])

		elif ttype == TelemetryType.UV_INDEX:
			if float(value) > float(self.ConfigManager.getModuleConfigByName('UVIndexAlert')):
				self.broadcast(method='onUVIndexAlert', exceptions=self.name, propagateToModules=True, args=[service])


	def getData(self, ttype: TelemetryType, siteId: str, service: str = None) -> Iterable:
		values = {'type': ttype.value, 'siteId': siteId}
		if service:
			values['service'] = service

		return self.databaseFetch(
			tableName='telemetry',
			query="SELECT value, timestamp FROM :__table__ WHERE type = :type and siteId = :siteId ORDER BY `timestamp` DESC LIMIT 1",
			values=values
		)
