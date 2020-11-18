import inspect
import json
import re
from pathlib import Path
from typing import Dict, Match, Optional

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.base.model.WidgetSizes import WidgetSizes


class Widget(ProjectAliceObject):
	DEFAULT_SIZE = WidgetSizes.w_small

	DEFAULT_OPTIONS = dict()
	CUSTOM_STYLE = {
		'background'        : '',
		'background-opacity': '1.0',
		'color'             : '',
		'font-size'         : '1.0',
		'titlebar'          : 'True'
	}


	def __init__(self, data: dict):
		super().__init__()

		self._id = int(data.get('id', -1))
		self._skill = data['skill']
		self._name = data['name']
		self._params = json.loads(data['params'])
		self._settings = json.loads(data['settings'])
		self._page = data['page']
		self._lang = self.loadLanguageFile()

		if not self._params:
			self._params = {
				'x'   : 0,
				'y'   : 0,
				'z'   : self.WidgetManager.getNextZIndex(self._page),
				'size': self.DEFAULT_SIZE.value
			}

		if self._id == -1:
			self.saveToDB()


	def _setId(self, wid: int):
		"""
		If the widget is created through the interface, the id is unknown until db insert
		:param wid: int
		"""
		self._id = wid


	def loadLanguageFile(self) -> Optional[Dict]:
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
		if self._id != -1:
			self.DatabaseManager.replace(
				tableName='widgets',
				query='REPLACE INTO :__table__ (id, skill, name, params, settings, page) VALUES (:id, :skill, :name, :params, :settings, :page)',
				callerName=self.WidgetManager.name,
				values={
					'id'      : self._id if self._id != 9999 else '',
					'skill'   : self._skill,
					'name'    : self._name,
					'params'  : json.dumps(self._params),
					'settings': json.dumps(self._settings),
					'page'    : self._page
				}
			)
		else:
			widgetId = self.DatabaseManager.insert(
				tableName='widgets',
				callerName=self.WidgetManager.name,
				values={
					'skill'   : self._skill,
					'name'    : self._name,
					'params'  : json.dumps(self._params),
					'settings': json.dumps(self._settings),
					'page'    : self._page
				}
			)

			self._setId(widgetId)


	def getCurrentDir(self) -> Path:
		return Path(inspect.getfile(self.__class__)).parent


	def html(self) -> str:
		try:
			file = self.getCurrentDir() / f'templates/{self.name}.html'
			fp = file.open()
			content = fp.read()
			content = re.sub(r'{{ lang\.([\w]*) }}', self.langReplace, content)

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
			return self._lang[self.LanguageManager.activeLanguage][key]
		except KeyError:
			return 'Missing string'


	def getOptions(self, key: str) -> str:
		try:
			return self._options[key]
		except KeyError:
			return 'Missing option'


	@property
	def id(self) -> int:
		return self._id


	@property
	def x(self) -> int:
		return self._params.get('x', 0)


	@x.setter
	def x(self, value: int):
		self._params['x'] = value


	@property
	def y(self) -> int:
		return self._params.get('y', 0)


	@y.setter
	def y(self, value: int):
		self._params['y'] = value


	@property
	def z(self) -> int:
		return self._params.get('z', 0)


	@z.setter
	def z(self, value: int):
		self._params['z'] = value


	@property
	def skill(self) -> str:
		return self._skill


	@skill.setter
	def skill(self, value: str):
		self._skill = value


	@property
	def name(self) -> str:
		return self._name


	@name.setter
	def name(self, value: str):
		self._name = value


	@property
	def params(self) -> dict:
		return self._params


	@params.setter
	def params(self, value: dict):
		self._params = value


	@property
	def settings(self) -> dict:
		return self._settings


	@settings.setter
	def settings(self, value: dict):
		self._settings = value


	@property
	def page(self) -> int:
		return self._page


	@page.setter
	def page(self, value: int):
		self._page = value


	# @property
	# def backgroundRGBA(self) -> str:
	# 	color = self._custStyle['background'].lstrip('#')
	# 	rgb = list(int(color[i:i + 2], 16) for i in (0, 2, 4))
	# 	rgb.append(self._custStyle['background-opacity'])
	# 	return ', '.join(str(i) for i in rgb)


	def toDict(self) -> dict:
		return {
			'id'      : self._id,
			'skill'   : self._skill,
			'name'    : self._name,
			'params'  : self._params,
			'settings': self._settings,
			'page'    : self._page
		}
