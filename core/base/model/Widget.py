import inspect
import json
import logging
import sqlite3

from pathlib import Path

from core.base.SuperManager import SuperManager


class Widget:

	SIZE = 'w'
	OPTIONS = dict()

	def __init__(self, data: sqlite3.Row):
		self._logger = logging.getLogger('ProjectAlice')
		self._name = data['name']
		self._parent = data['parent']

		self._state = data['state'] if 'state' in data.keys() else 0

		self._x = data['posx'] if 'posx' in data.keys() else 0
		self._y = data['posy'] if 'posy' in data.keys() else 0

		self._size = data['size'] if 'size' in data.keys() else self.SIZE
		options = data['options'] if 'options' in data.keys() else self.OPTIONS
		if options:
			self._options = json.loads(options)
		else:
			self._options = self.OPTIONS

		self._index = data['index']


	def saveToDB(self):
		SuperManager.getInstance().databaseManager.replace(
			tableName='widgets',
			query='REPLACE INTO :__table__ (parent, name, posx, posy, state, options, index) VALUES (:parent, :name, :posx, :posy, :state, :options, :index)',
			callerName=SuperManager.getInstance().moduleManager.name,
			values={
				'parent': self.parent,
				'name': self.name,
				'posx': self.x,
				'posy': self.y,
				'state': self.state,
				'options': json.dumps(self.options),
				'index': self.index
			}
		)


	def getCurrentDir(self) -> Path:
		return Path(inspect.getfile(self.__class__)).parent


	def html(self) -> str:
		try:
			file = self.getCurrentDir() / f'templates/{self.name}.html'
			return file.open().read()
		except:
			self._logger.warning(f"[{self.name}] Widget doesn't have html file")
			return ''


	@property
	def parent(self) -> str:
		return self._parent


	@parent.setter
	def parent(self, value: str):
		self._parent = value


	@property
	def name(self) -> str:
		return self._name


	@name.setter
	def name(self, value: str):
		self._name = value


	@property
	def x(self) -> int:
		return self._x


	@x.setter
	def x(self, value: int):
		self._x = value


	@property
	def y(self) -> int:
		return self._y


	@y.setter
	def y(self, value: int):
		self._y = value


	@property
	def state(self) -> int:
		return self._state


	@state.setter
	def state(self, value: int):
		self._state = value


	@property
	def size(self) -> str:
		return self._size


	@size.setter
	def size(self, value: str):
		self._size = value


	@property
	def options(self) -> dict:
		return self._options


	@options.setter
	def options(self, value: str):
		self._options = value


	@property
	def index(self) -> int:
		return self._index


	@index.setter
	def index(self, value: int):
		self._index = value


	def __repr__(self):
		return '---- WIDGET -----' + \
		       '\n Parent: ' + self.parent + \
		       '\n Name: ' + self.name + \
		       '\n Size: ' + self.size + \
		       '\n State: ' + str(self.state) + \
		       '\n PosX: ' + str(self.x) + \
		       '\n PosY: ' + str(self.y) +\
		       '\n Index: ' + str(self.index)