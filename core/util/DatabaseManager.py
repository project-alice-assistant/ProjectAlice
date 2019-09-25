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

			fullTableName = '{}_{}'.format(callerName, tableName)
			colsQuery = ', '.join(queries)
			colName = ''

			if colsQuery.count(' UNIQUE') > 1:
				colsQuery = colsQuery.replace(' UNIQUE', '')
				unique = list()
				for query in queries:
					if 'UNIQUE' in query:
						unique.append(query.split(' ')[0])

				unique = ', UNIQUE({})'.format(', '.join(unique))
			else:
				unique = ''

			try:
				query = "SELECT COUNT(name) FROM sqlite_master WHERE type = 'table' and name='{}'".format(fullTableName)
				cursor.execute(query)
				if cursor.fetchone()[0] < 1:
					self._logger.info('[{}] Missing data table "{}", creating it...'.format(self.name, fullTableName))
					try:
						cursor.execute('CREATE TABLE {} ({}{})'.format(fullTableName, colsQuery, unique))
						database.commit()
						continue
					except Exception:
						database.rollback()
						raise
			except Exception as e:
				self._logger.error('[{}] Something went wrong creating database table "{}" for component {}: {}'.format(self.name, fullTableName, callerName, e))
				continue

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


	def replace(self, tableName: str, query: str, callerName: str, values: dict = None) -> int:
		return self.insert(tableName, query, callerName, values)


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


	def update(self, tableName: str, callerName: str, values: dict, query: str = None, row: tuple = None) -> bool:
		if not query:
			updates = ['{} = :{}'.format(col, val) for col, val in values.items()]
			query = 'UPDATE :__table__ SET {} WHERE {} = {}'.format(' ,'.join(updates), row[0], row[1])

		query = self.basicChecks(tableName, query, callerName, values)
		if not query:
			raise Exception

		try:
			database = self.getConnection()
			cursor = database.cursor()
			cursor.execute(query, values)
		except Exception as e:
			self._logger.warning('[{}] Error updating data for component "{}" in table "{}": {}'.format(self.name, callerName, tableName, e))
			raise
		else:
			database.commit()
			cursor.close()
			database.close()
			return True



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

			if method == 'one':
				data = cursor.fetchone()
			else:
				data = cursor.fetchall()
		except Exception as e:
			self._logger.warning('[{}] Error fetching data for component "{}" in table "{}": {}'.format(self.name, callerName, tableName, e))
			return data
		else:
			cursor.close()
			database.close()
			return data


	def purge(self, tableName: str, callerName: str):
		query = 'DELETE FROM :__table__ WHERE 1'
		self.delete(tableName=tableName, callerName=callerName, query=query)


	def delete(self, tableName: str, callerName: str, query: str, values: dict = None):

		if not values:
			values = dict()

		query = self.basicChecks(tableName, query, callerName)
		if not query:
			return

		try:
			database = self.getConnection()
			cursor = database.cursor()
			cursor.execute(query, values)
		except Exception as e:
			self._logger.warning('[{}] Error deleting from table "{}" for component "{}": {}'.format(self.name, tableName, callerName, e))

			if database:
				database.rollback()
		else:
			database.commit()
			cursor.close()
			database.close()


	# noinspection SqlResolve
	def prune(self, tableName: str, callerName: str):
		"""
		Removes first X entries of a table
		:param tableName: str
		:param callerName: str
		:return:
		"""

		query = 'DELETE FROM :__table__ WHERE id in (SELECT id FROM :__table__ ORDER BY id LIMIT {})'.format(self.ConfigManager.getAliceConfigByName('autoPruneStoredData'))
		query = self.basicChecks(tableName, query, callerName)
		if not query:
			return

		try:
			database = self.getConnection()
			cursor = database.cursor()
			cursor.execute(query)
		except Exception as e:
			self._logger.warning('[{}] Error pruning table "{}" for component "{}": {}'.format(self.name, tableName, callerName, e))

			if database:
				database.rollback()
		else:
			database.commit()
			cursor.close()
			database.close()


	def basicChecks(self, tableName: str, query: str, callerName: str, values: dict = None) -> str:
		if ':__table__' not in query:
			self._logger.warning('[{}] The query must use \':__table__\' for the table name. Caller: {}'.format(self.name, callerName))
			return ''
		elif tableName.startswith('sqlite_'):
			self._logger.warning('[{}] You cannot access system tables. Caller; {}'.format(self.name, callerName))
			return ''
		elif values and ':__table__' in values:
			self._logger.warning("[{}] Cannot use reserved sqlite keyword \":__table__\". Caller: {}".format(self.name, callerName))
			return ''
		else:
			return query.replace(':__table__', callerName + '_' + tableName)
