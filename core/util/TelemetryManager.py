import time

from core.base.model.Manager import Manager
from core.util.model import TelemetryType


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
			self.logInfo(f'[{self.name}] Data storing is disabled')


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
			values={'type': ttype.value, 'value': value, 'service': service, 'siteId': siteId, 'timestamp': timestamp}
		)


	def getData(self, ttype: TelemetryType, siteId: str, service: str = None):
		values = {'type': ttype.value, 'siteId': siteId}
		if service:
			values['service'] = service

		return self.databaseFetch(
			tableName='telemetry',
			query=f"SELECT * FROM :__table__ WHERE type = :type and siteId = :siteId {'and service = :service' if service else ''} order by timestamp DESC LIMIT 1",
			values=values
		)