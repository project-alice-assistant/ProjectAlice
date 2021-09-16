#  Copyright (c) 2021
#
#  This file, DatabaseManager.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:47 CEST

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.ProjectAliceExceptions import DbConnectionError, InvalidQuery
from core.base.model.Manager import Manager
from core.commons import constants
from core.commons.CommonsManager import CommonsManager


# noinspection SqlResolve
class DatabaseManager(Manager):

	TABLE_TAG = ':__table__'

	def __init__(self):
		super().__init__()
		self._tables = list()


	def onStart(self):
		super().onStart()
		self.fetchTables()


	def fetchTables(self):
		database = self.getConnection()
		cursor = database.cursor()
		try:
			cursor.execute("SELECT name FROM main.sqlite_master WHERE type = 'table' and name NOT LIKE 'sqlite_%'")
			self._tables = cursor.fetchall()
			cursor.close()
			database.close()
		except sqlite3.Error as e:
			self.logError(f'Something went wrong fetching database tables: {e}')
			try:
				cursor.close()
				database.close()
			except:
				pass  # what else is there to do?
			return False


	def clearDB(self):
		Path(self.Commons.rootDir(), 'system/database/data.db').unlink()


	def getConnection(self) -> sqlite3.Connection:
		try:
			if self.ConfigManager.getAliceConfigByName('databaseProfiling'):
				self.logDebug(f'DB lock acquired by {CommonsManager.getFunctionCaller(depth=5)}->{CommonsManager.getFunctionCaller(depth=4)}->{CommonsManager.getFunctionCaller(depth=3)}')
			con = sqlite3.connect(constants.DATABASE_FILE, timeout=10)
		except sqlite3.Error as e:
			self.logError(f'Failed to connect to DB ({constants.DATABASE_FILE}): {e}')
			raise DbConnectionError()
		con.row_factory = sqlite3.Row
		return con


	def initDB(self, schema: dict, callerName: str) -> bool:
		database = self.getConnection()
		cursor = database.cursor()
		ret = True

		try:
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

				query = ''
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
					self.logError(f'Something went wrong creating database table **{fullTableName}** for component **{callerName}**. The query was "{query}": {e}.')
					continue

				try:
					cursor.execute(f'PRAGMA table_info({fullTableName})')
					rows = cursor.fetchall()
					installedColumns = {x[1]: x[2] for x in rows}

					cols = dict()
					for column in schema[tableName]:
						colName: str = column.split(' ')[0]
						if colName.lower().startswith('unique'):
							continue

						colType = column.split(' ')[1]
						cols[colName] = colType
						if colName not in installedColumns:
							oldColName = [val for val in installedColumns if colName.casefold() == val.casefold()]
							if oldColName:
								self.logWarning(f'Found a case-changed column from **{oldColName[0]}** to **{colName}** for table **{fullTableName}** in component **{callerName}**')
								cursor.execute(f'ALTER TABLE {fullTableName} RENAME COLUMN {oldColName[0]} TO {colName}')
							else:
								self.logWarning(f'Found a missing column **{colName}** for table **{fullTableName}** in component **{callerName}**')
								cursor.execute(f'ALTER TABLE {fullTableName} ADD COLUMN {colName} {colType}')

					database.commit()
				except sqlite3.Error as e:
					self.logError(f'Failed altering table **{fullTableName}** for component **{callerName}**: {e}')
					database.rollback()
					raise Exception

				try:
					cursor.execute(f'PRAGMA table_info({fullTableName})')
					rows = cursor.fetchall()
					installedColumns = {x[1]: x[2] for x in rows}

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
					raise Exception

			self.fetchTables()

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
		except:
			ret = False
		finally:
			cursor.close()
			database.close()
		return ret


	def dropTable(self, tableName: str, callerName: str) -> bool:
		database = self.getConnection()
		cursor = database.cursor()
		ret = True

		try:
			cursor.execute(f'DROP TABLE {callerName}_{tableName}')
			database.commit()
		except sqlite3.Error as e:
			self.logError(f'Failed dropping table **{tableName}** for component **{callerName}**: {e}')
			ret = False
		finally:
			try:
				cursor.close()
				database.close()
			except:
				pass  # Well, what's to do here....

		return ret


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

		database = self.getConnection()
		cursor = database.cursor()
		exception = None
		insertId = None

		try:
			try:
				startTime = time.time()
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
				if self.ConfigManager.getAliceConfigByName('databaseProfiling'):
					self.logDebug(f'It took {time.time() - startTime} seconds to INSERT {tableName} DB ')
		except Exception as e:
			exception = e

		try:
			cursor.close()
		except Exception as e:
			self.logError(f'FATAL ERROR: {e}')
		try:
			database.close()
		except Exception as e:
			self.logError(f'FATAL ERROR: {e}')

		if insertId is not None and not exception:
			return insertId
		elif insertId is None and not exception:
			raise Exception('Failed inserting into database')
		else:
			raise exception


	def update(self, tableName: str, callerName: str, values: dict = None, query: str = None, row: tuple = None) -> bool:
		if not query and not values:
			self.logWarning('Cannot update database with neither query or values set')
			return False

		if not query:
			updates = [f'{col} = :{col}' for col in values.keys()]
			query = f'UPDATE :__table__ SET {" ,".join(updates)} WHERE {row[0]} = "{row[1]}"'

		query = self.basicChecks(tableName, query, callerName, values)
		if not query:
			raise InvalidQuery

		database = self.getConnection()
		cursor = database.cursor()
		ret = True

		try:
			try:
				startTime = time.time()
				cursor.execute(query, values)
			except (DbConnectionError, sqlite3.Error) as e:
				self.logWarning(f'Error updating data for component **{callerName}** in table **{tableName}**: {e}')
				raise
			else:
				database.commit()
				if self.ConfigManager.getAliceConfigByName('databaseProfiling'):
					self.logDebug(f'It took {time.time() - startTime} seconds to UPDATE to {tableName} DB ')
		except:
			ret = False
		finally:
			try:
				cursor.close()
				database.close()
			except:
				pass  # what else is there to do??

		return ret


	def fetch(self, tableName: str, query: str, callerName: str, values: dict = None) -> List[Dict[str, Any]]:
		"""
		Fetch data from database. Returns a list of results in form of a dict
		:param values:
		:param tableName:
		:param query:
		:param callerName:
		:return: list
		"""
		if not values:
			values = dict()

		rows = list()
		query = self.basicChecks(tableName, query, callerName, values)
		if not query:
			return rows

		database = self.getConnection()
		cursor = database.cursor()

		try:
			startTime = time.time()
			cursor.execute(query, values)
			for row in cursor:
				rows.append(self.Commons.dictFromRow(row))

			if self.ConfigManager.getAliceConfigByName('databaseProfiling'):
				self.logDebug(f'It took {time.time() - startTime} seconds to FETCH from {tableName} DB ')
		except (DbConnectionError, sqlite3.Error) as e:
			self.logWarning(f'Error fetching data for component **{callerName}** in table **{tableName}**: {e}')
		finally:
			try:
				cursor.close()
				database.close()
			except:
				pass  # Well, what's to do here....

		return rows


	def purge(self, tableName: str, callerName: str):
		query = 'DELETE FROM :__table__ WHERE 1'
		self.delete(tableName=tableName, callerName=callerName, query=query)


	def delete(self, tableName: str, callerName: str, query: str = None, values: dict = None):

		if not values:
			values = dict()

		if not query:
			where = 'AND '.join([f'{k} = "{v}"' for k, v in values.items()])
			query = f'DELETE FROM :__table__ WHERE {where}'

		query = self.basicChecks(tableName, query, callerName)
		if not query:
			return

		database = self.getConnection()
		try:
			startTime = time.time()
			database.execute(query, values)
			database.commit()
			if self.ConfigManager.getAliceConfigByName('databaseProfiling'):
				self.logDebug(f'It took {time.time() - startTime} seconds to DELETE in {tableName} DB ')
		except DbConnectionError as e:
			self.logWarning(f'Error deleting from table **{tableName}** for component **{callerName}**: {e}')
		except sqlite3.Error as e:
			self.logWarning(f'Error deleting from table **{tableName}** for component **{callerName}**: {e}')
			database.rollback()

		try:
			database.close()
		except:
			pass  # Well, what's to do here....


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

		database = self.getConnection()
		try:
			startTime = time.time()
			database.execute(query)
			database.commit()
			if self.ConfigManager.getAliceConfigByName('databaseProfiling'):
				self.logDebug(f'It took {time.time() - startTime} seconds to PRUNE {tableName} DB ')
		except DbConnectionError as e:
			self.logWarning(f'Error pruning table **{tableName}** for component **{callerName}**: {e}')
		except sqlite3.Error as e:
			self.logWarning(f'Error pruning table **{tableName}** for component **{callerName}**: {e}')
			database.rollback()
		finally:
			database.close()


	def basicChecks(self, tableName: str, query: str, callerName: str, values: dict = None) -> Optional[str]:
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
