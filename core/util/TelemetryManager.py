import time

import core.base.Managers as managers
from core.base.Manager import Manager
from core.util.model import TelemetryType


class TelemetryManager(Manager):
	NAME = 'TelemetryManager'

	DATABASE = {
		'telemetry': [
			'id integer PRIMARY KEY',
			'type TEXT NOT NULL',
			'value TEXT NOT NULL',
			'service TEXT',
			'siteId TEXT NOT NULL',
			'timestamp INTEGER NOT NULL'
		]
	}


	def __init__(self, mainClass):
		super().__init__(mainClass, self.NAME, self.DATABASE)
		managers.TelemetryManager = self

		if not managers.ConfigManager.getAliceConfigByName('enableDataStoring'):
			self.isActive = False
			self._logger.info('[{}] Data storing is disabled'.format(self.name))

		self._data = list


	def onQuarterHour(self):
		if managers.ConfigManager.getAliceConfigByName('autoPruneStoredData') > 0:
			self.pruneTable('telemetry')


	# noinspection SqlResolve
	def loadData(self):
		if not self.isActive:
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
