import sqlite3
import typing

from core.base.model.Manager import Manager
from core.commons import commons


class DatabaseManager(Manager):

	NAME = 'DatabaseManager'

	def __init__(self):
		super().__init__(self.NAME)
		self._tables = list()


	def onStart(self):
		super().onStart()

		database = self.getConnection()
		cursor = database.cursor()
		try:
			cursor.execute("SELECT name FROM main.sqlite_master WHERE type = 'table' and name NOT LIKE 'sqlite_%'")
			self._tables = cursor.fetchall()
		except Exception as e:
			self._logger.error('[{}] Something went wrong fetching database tables: {}'.format(self.name, e))
			return False


	@staticmethod
	def getConnection() -> sqlite3.Connection:
		con = sqlite3.connect(commons.getDatabaseFile())
		con.row_factory = sqlite3.Row
		return con


	def initDB(self, schema: dict, callerName: str) -> bool:
		database = self.getConnection()
		cursor = database.cursor()

		# First check for new tables and columns addition/deprecation
		for tableName, queries in schema.items():
			colName = ''
			fullTableName = '{}_{}'.format(callerName, tableName)
			colsQuery = ', '.join(queries)
			try:
				cursor.execute('CREATE TABLE IF NOT EXISTS {} ({})'.format(fullTableName, colsQuery))
				database.commit()
			except Exception as e:
				self._logger.error('[{}] Something went wrong creating database table "{}" for component {}: {}'.format(self.name, fullTableName, callerName, e))
				database.rollback()
				return False

			try:
				cursor.execute('PRAGMA table_info({})'.format(fullTableName))
				rows = cursor.fetchall()
				installedColumns = [x[1] for x in rows]

				cols = list()
				for column in schema[tableName]:
					colName = column.split(' ')[0]
					cols.append(colName)
					if colName not in installedColumns:
						self._logger.info('[{}] Found a missing column "{}" for table "{}" in component "{}"'.format(self.name, colName, fullTableName, callerName))
						cursor.execute('ALTER TABLE {} ADD COLUMN {}'.format(fullTableName, column))

				database.commit()
			except Exception as e:
				self._logger.info('[{}] Failed altering table "{}" for component "{}": {}'.format(self.name, fullTableName, callerName, e))
				database.rollback()
				return False

			try:
				doUpdate = False
				for column in installedColumns:
					if column not in cols:
						self._logger.info('[{}] Found a deprecated column "{}" for table "{}" in component "{}"'.format(self.name, colName, fullTableName, callerName))
						doUpdate = True

				if doUpdate:
					cursor.execute('ALTER TABLE {} RENAME TO {}'.format(fullTableName, 'bak_' + fullTableName))
					cursor.execute('CREATE TABLE {} ({})'.format(fullTableName, colsQuery))
					cursor.execute('INSERT INTO {} SELECT {} FROM {}'.format(fullTableName, ', '.join(cols), 'bak_' + fullTableName))
					cursor.execute('DROP TABLE {}'.format('bak_' + fullTableName))
					database.commit()

			except Exception as e:
				self._logger.error('[{}] Something went wrong initializing database for module {}: {}'.format(self.name, callerName, e))
				database.rollback()
				return False

		# Let's check if we did not drop a table since an older version
		for tableName in self._tables:
			tableName = tableName['name']
			if not tableName.startswith('sqlite_') and tableName.startswith(callerName + '_') and tableName.split('_')[1] not in schema:
				self._logger.info('[{}] Found a deprecated table "{}" for component "{}"'.format(self.name, tableName, callerName))

				try:
					cursor.execute('DROP TABLE {}'.format(tableName))
					database.commit()
				except Exception as e:
					self._logger.error('[{}] Failed dropping deprecated table "{}" for component "{}": {}'.format(self.name, tableName, callerName, e))
					continue

		cursor.close()
		database.close()
		return True


	def insert(self, tableName: str, query: str, callerName: str, values: dict = None) -> int:
		"""
		Insert data in database
		:param values:
		:param tableName:
		:param query:
		:param callerName:
		:return: list
		"""
		if not values:
			values = dict()

		query = self.basicChecks(tableName, query, callerName, values)

		if not query:
			raise Exception

		database = None
		try:
			database = self.getConnection()
			cursor = database.cursor()

			cursor.execute(query, values)
			insertId = cursor.lastrowid
		except Exception as e:
			self._logger.warning('[{}] Error inserting data for component "{}" in table "{}": {}'.format(self.name, callerName, tableName, e))

			if database:
				database.rollback()

			raise
		else:
			database.commit()
			cursor.close()
			database.close()
			if insertId:
				return insertId
			else:
				raise Exception


	def fetch(self, tableName: str, query: str, callerName: str, values: dict = None, method: str = 'one') -> typing.Iterable:
		"""
		Fetch data from database
		:param values:
		:param tableName:
		:param query:
		:param callerName:
		:param method: one or all
		:return: list
		"""
		if not values:
			values = dict()

		data = list()

		query = self.basicChecks(tableName, query, callerName, values)
		if not query:
			return data

		try:
			database = self.getConnection()
			cursor = database.cursor()

			cursor.execute(query, values)

			if method == 'all':
				data = cursor.fetchall()
			else:
				data = cursor.fetchone()
		except Exception as e:
			self._logger.warning('[{}] Error fetching data for component "{}" in table "{}": {}'.format(self.name, callerName, tableName, e))
			return data
		else:
			cursor.close()
			database.close()
			return data


	# noinspection SqlResolve
	def prune(self, tableName: str, callerName: str):
		"""
		Removes first X entries of a table
		:param tableName: str
		:param callerName: str
		:return:
		"""
		database = None
		try:
			database = self.getConnection()
			cursor = database.cursor()

			cursor.execute('DELETE FROM {} WHERE id in (SELECT id FROM {} ORDER BY id LIMIT {})'.format(tableName, tableName, self.ConfigManager.getAliceConfigByName('autoPruneStoredData')))
		except Exception as e:
			self._logger.warning('[{}] Error pruning table "{}" for component "{}": {}'.format(self.name, tableName, callerName, e))

			if database:
				database.rollback()
		else:
			database.commit()
			cursor.close()
			database.close()


	def basicChecks(self, tableName: str, query: str, callerName: str, values: dict) -> str:
		if ':__table__' not in query:
			self._logger.warning('[{}] The query must use \':__table__\' for the table name'.format(self.name))
			return ''
		elif tableName.startswith('sqlite_'):
			self._logger.warning('[{}] You cannot access system tables'.format(self.name))
			return ''
		elif ':__table__' in values:
			self._logger.warning("[{}] Cannot use reserved sqlite keyword \":__table__\"")
			return ''
		else:
			return query.replace(':__table__', callerName + '_' + tableName)
