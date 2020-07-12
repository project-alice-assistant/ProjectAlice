import inspect
import json
import sqlite3
from pathlib import Path
from textwrap import dedent
from typing import Dict, Match, Optional

import re

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.base.model.WidgetSizes import WidgetSizes


class Widget(ProjectAliceObject):
	DEFAULT_SIZE = WidgetSizes.w

	DEFAULT_OPTIONS = dict()
	CUSTOM_STYLE = {
		'background': '',
		'background-opacity': '1.0',
		'color': '',
		'font-size': '1.0',
		'titlebar': 'True'
	}

	def __init__(self, data: sqlite3.Row):
		super().__init__()
		self._name = data['name']
		self._parent = data['parent']
		self._skillInstance = None

		# sqlite3.Row does not support .get like dicts
		# Many checks here because of NOT NULL DB constraints
		updateWidget = False
		if 'state' in data.keys() and data['state']:
			self._state = int(data['state'])
		else:
			self._state = 0
			updateWidget = True

		if 'posx' in data.keys() and data['posx']:
			self._x = data['posx']
		else:
			self._x = 10
			updateWidget = True

		if 'posy' in data.keys() and data['posy']:
			self._y = data['posy']
		else:
			self._y = 10
			updateWidget = True

		if 'height' in data.keys() and data['height']:
			self._height = data['height']
		else:
			self._height = 0
			updateWidget = True

		if 'width' in data.keys() and data['width']:
			self._width = data['width']
		else:
			self._width = 0
			updateWidget = True

		self._size = self.DEFAULT_SIZE.value

		self._options = self.DEFAULT_OPTIONS
		if 'options' in data.keys():
			self._options.update(json.loads(data['options']))

		self._custStyle = self.CUSTOM_STYLE.copy()
		if 'custStyle' in data.keys() and data['custStyle']:
			self._custStyle.update(json.loads(data['custStyle']))
		else:
			updateWidget = True

		if 'zindex' in data.keys() and data['zindex'] is not None:
			self._zindex = data['zindex']
		else:
			self._zindex = 999
			updateWidget = True

		if updateWidget:
			self.saveToDB()

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
			query='REPLACE INTO :__table__ (parent, name, posx, posy, height, width, state, options, custStyle, zindex) VALUES (:parent, :name, :posx, :posy, :height, :width, :state, :options, :custStyle, :zindex)',
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
				'custStyle': json.dumps(self.custStyle),
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
			content = re.sub(r'{{ lang\.([\w]*) }}', self.langReplace, content)
			content = re.sub(r'{{ options\.([\w]*) }}', self.optionsReplace, content)

			return content
		except:
			self.logWarning(f"Widget doesn't have html file")
			return ''


	def langReplace(self, match: Match):
		return self.getLanguageString(match.group(1))

	def optionsReplace(self, match: Match):
		return self.getOptions(match.group(1))


	def getLanguageString(self, key: str) -> str:
		try:
			return self._language[self.LanguageManager.activeLanguage][key]
		except KeyError:
			return 'Missing string'


	def getOptions(self, key: str) -> str:
		try:
			return self._options[key]
		except KeyError:
			return 'Missing option'


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
	def custStyle(self) -> dict:
		return self._custStyle


	@custStyle.setter
	def custStyle(self, value: str):
		self._custStyle = value


	@property
	def backgroundRGBA(self) -> str:
		color = self._custStyle['background'].lstrip('#')
		rgb = list(int(color[i:i + 2], 16) for i in (0, 2, 4))
		rgb.append(self._custStyle['background-opacity'])
		return ', '.join(str(i) for i in rgb)


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
