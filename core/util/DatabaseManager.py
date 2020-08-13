import sqlite3
import typing
from pathlib import Path

from core.ProjectAliceExceptions import DbConnectionError, InvalidQuery
from core.base.model.Manager import Manager
from core.commons import constants


# noinspection SqlResolve
class DatabaseManager(Manager):

	TABLE_TAG = ':__table__'

	def __init__(self):
		super().__init__()
		self._tables = list()


	def onStart(self):
		super().onStart()

		database = self.getConnection()
		cursor = database.cursor()
		try:
			cursor.execute("SELECT name FROM main.sqlite_master WHERE type = 'table' and name NOT LIKE 'sqlite_%'")
			self._tables = cursor.fetchall()
		except sqlite3.Error as e:
			self.logError(f'Something went wrong fetching database tables: {e}')
			return False


	def clearDB(self):
		Path(self.Commons.rootDir(), 'system/database/data.db').unlink()


	def getConnection(self) -> sqlite3.Connection:
		try:
			con = sqlite3.connect(constants.DATABASE_FILE)
		except sqlite3.Error as e:
			self.logError(f'Failed to connect to DB ({constants.DATABASE_FILE}): {e}')
			raise DbConnectionError()
		con.row_factory = sqlite3.Row
		return con


	def initDB(self, schema: dict, callerName: str) -> bool:
		database = self.getConnection()
		cursor = database.cursor()

		# First check for new tables and columns addition/deprecation/type changes
		for tableName, queries in schema.items():

			fullTableName = f'{callerName}_{tableName}'
			colsQuery = ', '.join(queries)

			if colsQuery.count(' UNIQUE') > 1:
				colsQuery = colsQuery.replace(' UNIQUE', '')
				uniqueList = [query.split(' ')[0] for query in queries if 'UNIQUE' in query]
				unique = f", UNIQUE({', '.join(uniqueList)})"
			else:
				unique = ''

			try:
				query = f"SELECT COUNT(name) FROM sqlite_master WHERE type = 'table' and name='{fullTableName}'"
				cursor.execute(query)
				if cursor.fetchone()[0] < 1:
					self.logInfo(f'Missing data table **{fullTableName}**, creating it...')
					try:
						cursor.execute(f'CREATE TABLE {fullTableName} ({colsQuery}{unique})')
						database.commit()
						continue
					except sqlite3.Error:
						database.rollback()
						raise
			except sqlite3.Error as e:
				self.logError(f'Something went wrong creating database table **{fullTableName}** for component **{callerName}**: {e}')
				continue

			try:
				cursor.execute(f'PRAGMA table_info({fullTableName})')
				rows = cursor.fetchall()
				installedColumns = {x[1]: x[2] for x in rows}

				cols = dict()
				for column in schema[tableName]:
					colName = column.split(' ')[0]
					colType = column.split(' ')[1]
					cols[colName] = colType
					if colName not in installedColumns:
						self.logWarning(f'Found a missing column **{colName}** for table **{fullTableName}** in component **{callerName}**')
						cursor.execute(f'ALTER TABLE {fullTableName} ADD COLUMN `{colName}` `{colType}`')

				database.commit()
			except sqlite3.Error as e:
				self.logError(f'Failed altering table **{fullTableName}** for component **{callerName}**: {e}')
				database.rollback()
				return False

			try:
				doUpdate = False
				for column in installedColumns:
					if column not in cols:
						self.logInfo(f'Found a deprecated column **{column}** for table **{fullTableName}** in component **{callerName}**')
						doUpdate = True
					elif installedColumns[column].lower() != cols[column].lower():
						self.logInfo(f'Column **{column}** has changed data type for component **{callerName}**')
						doUpdate = True

				if doUpdate:
					cursor.execute(f"ALTER TABLE {fullTableName} RENAME TO {'bak_' + fullTableName}")
					cursor.execute(f'CREATE TABLE {fullTableName} ({colsQuery})')
					cursor.execute(f"INSERT INTO {fullTableName} SELECT {', '.join(cols)} FROM {'bak_' + fullTableName}")
					cursor.execute(f"DROP TABLE {'bak_' + fullTableName}")
					database.commit()

			except sqlite3.Error as e:
				self.logError(f'Something went wrong initializing database for skill {callerName}: {e}')
				database.rollback()
				return False

		# Let's check if we did not drop a table since an older version
		for tableName in self._tables:
			tableName = tableName['name']
			if not tableName.startswith('sqlite_') and tableName.startswith(callerName + '_') and tableName.split('_')[1] not in schema:
				self.logWarning(f'Found a deprecated table **{tableName}** for component **{callerName}**')

				try:
					cursor.execute(f'DROP TABLE {tableName}')
					database.commit()
				except sqlite3.Error as e:
					self.logError(f'Failed dropping deprecated table **{tableName}** for component **{callerName}**: {e}')
					continue

		cursor.close()
		database.close()
		return True


	def dropTable(self, tableName: str, callerName: str) -> bool:
		database = self.getConnection()
		cursor = database.cursor()

		try:
			cursor.execute(f'DROP TABLE {callerName}_{tableName}')
			database.commit()
			return True
		except sqlite3.Error as e:
			self.logError(f'Failed dropping table **{tableName}** for component **{callerName}**: {e}')
			return False


	def replace(self, tableName: str, query: str = None, callerName: str = None, values: dict = None) -> int:
		if not query:
			cols = ', '.join(values)
			data = ', :'.join(values)
			query = f'REPLACE INTO :__table__ ({cols}) VALUES (:{data})'

		return self.insert(tableName, query, callerName, values)


	def insert(self, tableName: str, query: str = None, callerName: str = None, values: dict = None) -> int:
		"""
		Insert data in database
		:param values:
		:param tableName:
		:param query:
		:param callerName:
		:return: list
		"""
		if not values:
			raise Exception('Cannot DB insert without values...')

		if not callerName:
			callerName = self.Commons.getFunctionCaller()

		if not query:
			cols = ', '.join(values)
			data = ', :'.join(values)
			query = f'INSERT INTO :__table__ ({cols}) VALUES (:{data})'

		query = self.basicChecks(tableName, query, callerName, values)

		if not query:
			raise InvalidQuery

		database = None
		try:
			database = self.getConnection()
			cursor = database.cursor()

			cursor.execute(query, values)
			insertId = cursor.lastrowid
		except DbConnectionError as e:
			self.logWarning(f'Error inserting data for component **{callerName}** in table **{tableName}**: {e}')
			raise
		except sqlite3.Error as e:
			self.logWarning(f'Error inserting data for component **{callerName}** in table **{tableName}**: {e}')
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
			updates = [f'{col} = "{val}"' for col, val in values.items()]
			query = f'UPDATE :__table__ SET {" ,".join(updates)} WHERE {row[0]} = "{row[1]}"'

		query = self.basicChecks(tableName, query, callerName, values)
		if not query:
			raise InvalidQuery

		try:
			database = self.getConnection()
			cursor = database.cursor()
			cursor.execute(query, values)
		except (DbConnectionError, sqlite3.Error) as e:
			self.logWarning(f'Error updating data for component **{callerName}** in table **{tableName}**: {e}')
			raise
		else:
			database.commit()
			cursor.close()
			database.close()
			return True


	#TODO this not really right, right now it either returns a list of sqlite3.Row when the method is not 'one',
	# a sqlite2.Row or None when it is None and when there is an exception or no query sqlite3.Row() is a broken syntax
	# -> will throw an TypeError (should probably return a empty list or None instead)
	def fetch(self, tableName: str, query: str, callerName: str, values: dict = None, method: str = 'one') -> sqlite3.Row:
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

		query = self.basicChecks(tableName, query, callerName, values)
		if not query:
			return sqlite3.Row()

		try:
			database = self.getConnection()
			cursor = database.cursor()

			cursor.execute(query, values)

			if method == 'one':
				data = cursor.fetchone()
			else:
				data = cursor.fetchall()
		except (DbConnectionError, sqlite3.Error) as e:
			self.logWarning(f'Error fetching data for component **{callerName}** in table **{tableName}**: {e}')
			return sqlite3.Row()
		else:
			cursor.close()
			database.close()
			return data


	def purge(self, tableName: str, callerName: str):
		query = 'DELETE FROM :__table__ WHERE 1'
		self.delete(tableName=tableName, callerName=callerName, query=query)


	def delete(self, tableName: str, callerName: str, query: str = None, values: dict = None):

		if not values:
			values = dict()

		if not query:
			where = ', '.join([f'{k} = "{v}"' for k,v in values.items()])
			query = f'DELETE FROM :__table__ WHERE {where}'

		query = self.basicChecks(tableName, query, callerName)
		if not query:
			return

		database = None
		try:
			database = self.getConnection()
			database.execute(query, values)
		except DbConnectionError as e:
			self.logWarning(f'Error deleting from table **{tableName}** for component **{callerName}**: {e}')
		except sqlite3.Error as e:
			self.logWarning(f'Error deleting from table **{tableName}** for component **{callerName}**: {e}')
			database.rollback()
			database.close()
		else:
			database.commit()
			database.close()


	# noinspection SqlResolve
	def prune(self, tableName: str, callerName: str):
		"""
		Removes first X entries of a table
		:param tableName: str
		:param callerName: str
		:return:
		"""

		query = f"DELETE FROM :__table__ WHERE id not in (SELECT id FROM :__table__ ORDER BY id DESC LIMIT {self.ConfigManager.getAliceConfigByName('autoPruneStoredData')})"
		query = self.basicChecks(tableName, query, callerName)
		if not query:
			return

		database = None
		try:
			database = self.getConnection()
			database.execute(query)
		except DbConnectionError as e:
			self.logWarning(f'Error pruning table **{tableName}** for component **{callerName}**: {e}')
		except sqlite3.Error as e:
			self.logWarning(f'Error pruning table **{tableName}** for component **{callerName}**: {e}')
			database.rollback()
			database.close()
		else:
			database.commit()
			database.close()


	def basicChecks(self, tableName: str, query: str, callerName: str, values: dict = None) -> typing.Optional[str]:
		if self.TABLE_TAG not in query:
			self.logWarning(f'The query must use \':__table__\' for the table name. Caller: {callerName}')
			return None
		elif tableName.startswith('sqlite_'):
			self.logWarning(f'You cannot access system tables. Caller; {callerName}')
			return None
		elif values and self.TABLE_TAG in values:
			self.logWarning(f"Cannot use reserved sqlite keyword \":__table__\". Caller: {callerName}")
			return None
		else:
			return query.replace(self.TABLE_TAG, callerName + '_' + tableName)
