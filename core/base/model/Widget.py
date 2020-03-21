import inspect
import json
import sqlite3
from pathlib import Path
from textwrap import dedent
from typing import Dict, Match, Optional

import re

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.base.model.widgetSizes import WidgetSizes


class Widget(ProjectAliceObject):
	SIZE = WidgetSizes.w

	OPTIONS = dict()

	def __init__(self, data: sqlite3.Row):
		super().__init__()
		self._name = data['name']
		self._parent = data['parent']
		self._skillInstance = None

		# sqlite3.Row does not support .get like dicts
		self._state = data['state'] if 'state' in data.keys() else 0
		self._x = data['posx'] if 'posx' in data.keys() else 0
		self._y = data['posy'] if 'posy' in data.keys() else 0
		self._height = data['height'] if 'height' in data.keys() else 0
		self._width = data['width'] if 'width' in data.keys() else 0
		self._size = self.SIZE.value

		self._options = self.OPTIONS
		if 'options' in data.keys():
			self._options.update(json.loads(data['options']))

		self._zindex = data['zindex'] if 'zindex' in data.keys() else 9999
		self._language = self.loadLanguage()


	def setParentSkillInstance(self, skill):
		self._skillInstance = skill


	def loadLanguage(self) -> Optional[Dict]:
		try:
			file = self.getCurrentDir() / f'lang/{self.name}.lang.json'
			with file.open() as fp:
				return json.load(fp)
		except FileNotFoundError:
			self.logWarning(f'Missing language file for widget {self.name}')
			return None
		except Exception:
			self.logWarning(f"Couldn't import language file for widget {self.name}")
			return None


	# noinspection SqlResolve
	def saveToDB(self):
		self.DatabaseManager.replace(
			tableName='widgets',
			query='REPLACE INTO :__table__ (parent, name, posx, posy, height, width, state, options, zindex) VALUES (:parent, :name, :posx, :posy, :height, :width, :state, :options, :zindex)',
			callerName=self.SkillManager.name,
			values={
				'parent': self.parent,
				'name': self.name,
				'posx': self.x,
				'posy': self.y,
				'height': self.height,
				'width': self.width,
				'state': self.state,
				'options': json.dumps(self.options),
				'zindex': self.zindex
			}
		)


	def getCurrentDir(self) -> Path:
		return Path(inspect.getfile(self.__class__)).parent


	def html(self) -> str:
		try:
			file = self.getCurrentDir() / f'templates/{self.name}.html'
			fp = file.open()
			content = fp.read()
			# noinspection PyTypeChecker
			content = re.sub(r'{{ lang\.([\w]*) }}', self.langReplace, content)

			return content
		except:
			self.logWarning(f"Widget doesn't have html file")
			return ''


	def langReplace(self, match: Match):
		return self.getLanguageString(match.group(1))


	def getLanguageString(self, key: str) -> str:
		try:
			return self._language[self.LanguageManager.activeLanguage][key]
		except KeyError:
			return 'Missing string'


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
	def size(self) -> WidgetSizes:
		return self._size


	@size.setter
	def size(self, value: str):
		self._size = value


	@property
	def height(self) -> int:
		return self._height


	@height.setter
	def height(self, value: int):
		self._height = value


	@property
	def width(self) -> int:
		return self._width


	@width.setter
	def width(self, value: int):
		self._width = value


	@property
	def options(self) -> dict:
		return self._options


	@options.setter
	def options(self, value: str):
		self._options = value


	@property
	def zindex(self) -> int:
		return self._zindex


	@zindex.setter
	def zindex(self, value: int):
		self._zindex = value


	@property
	def skillInstance(self):
		return self._skillInstance


	def __repr__(self):
		return dedent(f'''\
			---- WIDGET -----
			 Parent: {self.parent}
			 Name: {self.name}
			 Size: {self.size}
			 CustomSize: {self.height}/{self.width}
			 State: {self.state}
			 PosX: {self.x}
			 PosY: {self.y}
			 Z-Index: {self.zindex}\
		''')
