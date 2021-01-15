import importlib
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Union

from core.base.model.Manager import Manager
from core.webui.model.Widget import Widget
from core.webui.model.WidgetPage import WidgetPage


class WidgetManager(Manager):
	DEFAULT_ICON = 'fas fa-biohazard'

	WIDGETS_TABLE = 'widgets'
	WIDGET_PAGES_TABLE = 'widgetPages'
	WIDGET_LAYOUT_PRESETS_TABLE = 'widgetLayoutPresets'

	DATABASE = {
		WIDGETS_TABLE              : [
			'id INTEGER PRIMARY KEY',  # NOSONAR
			'skill TEXT NOT NULL',
			'name TEXT NOT NULL',
			"params TEXT NOT NULL DEFAULT '{}'",
			"settings TEXT NOT NULL DEFAULT '{}'",
			'page INTEGER NOT NULL DEFAULT 0'
		],
		WIDGET_PAGES_TABLE         : [
			'id INTEGER PRIMARY KEY',
			'icon TEXT NOT NULL',
			'position INTEGER NOT NULL'
		],
		WIDGET_LAYOUT_PRESETS_TABLE: [
			'id INTEGER PRIMARY KEY',
			'name TEXT NOT NULL',
			'layout TEXT NOT NULL'
		]
	}


	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)
		self._widgetTemplates: Dict[str, List[Path]] = dict()
		self._widgets: Dict[int, Widget] = dict()
		self._pages = dict()
		self._widgetsByIndex = dict()
		self._widgetLayoutPresets = dict()


	def onStart(self):
		super().onStart()
		self.loadPages()
		self.loadWidgets()
		self.getNextZIndex(1)


	def loadWidgetLayoutPresets(self):
		data = self.databaseFetch(tableName=self.WIDGET_LAYOUT_PRESETS_TABLE, method='all')
		self._widgetLayoutPresets = {preset['name'].lower: preset['layout'] for preset in data}
		self.logInfo(f'Loaded {self._widgetLayoutPresets} widget layout preset', plural='preset')


	def saveWidgetLayout(self, presetName: str):
		layout = dict()
		layout['name'] = presetName.lower()
		for page in self._pages:
			layout[page.id] = dict()
			layout[page.id]['icon'] = page.icon
			layout[page.id]['position'] = page.position
			layout[page.id]['widgets'] = dict()
			for wid, widget in self._widgets.items():
				if widget.page != page.id:
					continue


	def loadWidgets(self):
		count = 0
		for skill in self.SkillManager.allSkills.values():
			try: #failed skills don't have any .widgets at all and crash the manager!
				if not skill.widgets:
					continue
			except:
				continue

			count += len(skill.widgets)
			self._widgetTemplates[skill.name] = skill.widgets

		allTemplates = list()
		for widgets in self._widgetTemplates.values():
			allTemplates += widgets

		# Cleanup possible deprecated widgets
		data = self.databaseFetch(tableName=self.WIDGETS_TABLE, method='all')

		for widget in data:
			if widget['skill'] not in self._widgetTemplates or widget['name'] not in allTemplates:

				self.logInfo(f'Widget **{widget["name"]}** is deprecated, removing')
				# noinspection SqlResolve
				self.DatabaseManager.delete(
					tableName=self.WIDGETS_TABLE,
					callerName=self.name,
					values={
						'parent': widget['skill'],
						'name'  : widget['name']
					}
				)
				continue

			# Create widget instance
			instance = self.instanciateWidget(widget)
			if not instance:
				continue

			self._widgets[instance.id] = instance

		self.logInfo(f'Loaded **{count}** template from {len(self._widgetTemplates)} skill', plural=['template', 'skill'])
		self.logInfo(f'Loaded {len(self._widgets)} active widget', plural='widget')


	def instanciateWidget(self, widgetData: Union[sqlite3.Row, dict]) -> Optional[Widget]:
		if isinstance(widgetData, sqlite3.Row):
			widgetData = self.Commons.dictFromRow(widgetData)

		skill = self.SkillManager.getSkillInstance(widgetData['skill'])
		if not skill:
			self.logWarning(f'Skill {widgetData["skill"]} for widget {widgetData["name"]} is not instanciated, skipping widget')
			return None

		try:
			resource = skill.getResource(f'widgets/{widgetData["name"]}').stem
			widgetImport = importlib.import_module(f'skills.{skill.name}.widgets.{resource}')

			klass = getattr(widgetImport, widgetData["name"])
			return klass(widgetData)
		except ImportError as e:
			self.logError(f"Couldn't import widget **{widgetData['name']}**: {e}")
			return None
		except AttributeError as e:
			self.logError(f"Couldn't find main class for widget **{widgetData['name']}**: {e}")
			return None
		except Exception as e:
			self.logError(f"Couldn't instanciate widget **{widgetData['name']}**: {e}")
			return None


	def addWidget(self, skillName: str, widgetName: str, pageId: int) -> Optional[Widget]:
		if skillName not in self._widgetTemplates or widgetName not in self._widgetTemplates[skillName]:
			self.logWarning(f'Tried to add widget **{widgetName}** from skill **{skillName}** but no template was found')
			return None

		if pageId not in self._pages:
			self.logWarning(f'Tried to add widget **{widgetName}** from skill **{skillName}** to page id **{pageId}** but the page doesn\'t exist')
			return None

		instance = self.instanciateWidget({
			'skill'   : skillName,
			'name'    : widgetName,
			'params'  : '{}',
			'settings': '{}',
			'page'    : pageId
		})

		self._widgets[instance.id] = instance

		return instance


	def loadPages(self):
		data = self.databaseFetch(tableName=self.WIDGET_PAGES_TABLE, method='all')
		if data:
			self._pages = {row['id']: WidgetPage(row) for row in data}
		else:
			# Insert default page
			self.databaseInsert(
				tableName=self.WIDGET_PAGES_TABLE,
				values = {
					'icon'    : self.DEFAULT_ICON,
					'position': 0
				}
			)
			return self.loadPages()

		self.logInfo(f'Loaded **{len(self._pages)}** page', plural='page')


	def addPage(self) -> Optional[WidgetPage]:
		try:
			maxPos = 0
			for page in self._pages.values():
				if page.position > maxPos:
					maxPos = page.position

			pageId = self.databaseInsert(
				tableName=self.WIDGET_PAGES_TABLE,
				values = {
					'icon'    : self.DEFAULT_ICON,
					'position': maxPos + 1
				}
			)

			page = WidgetPage({
				'id'      : pageId,
				'icon'    : 'fas fa-biohazard',
				'position': maxPos + 1
			})
			self._pages[pageId] = page

			return page
		except Exception as e:
			self.logError(f'Failed adding new widget page: {e}')
			return None


	def updatePageIcon(self, pageId: int, icon: str):
		self.DatabaseManager.update(
			tableName=self.WIDGET_PAGES_TABLE,
			callerName=self.name,
			values={
				'icon': icon
			},
			row=('id', pageId)
		)
		self._pages[pageId].icon = icon


	def removePage(self, pageId: int):
		position = self._pages[pageId].position
		for pid, page in self._pages.items():
			if page.position <= position:
				continue

			page.position -= 1
			self.DatabaseManager.update(
				tableName=self.WIDGET_PAGES_TABLE,
				callerName=self.name,
				values={
					'position': page.position
				},
				row=('id', pid)
			)
		self._pages.pop(pageId, None)

		self.DatabaseManager.delete(
			tableName=self.WIDGET_PAGES_TABLE,
			callerName=self.name,
			values={
				'id': pageId
			}
		)

		self.DatabaseManager.delete(
			tableName=self.WIDGETS_TABLE,
			callerName=self.name,
			values={
				'page': pageId
			}
		)

		tmp = self._widgets.copy()
		for wid, widget in tmp.items():
			if widget.page == pageId:
				self._widgets.pop(wid, None)


	def removeWidget(self, widgetId: int):
		self.DatabaseManager.delete(
			tableName=self.WIDGETS_TABLE,
			callerName=self.name,
			values={
				'id': widgetId
			}
		)
		self._widgets.pop(widgetId, None)


	def skillRemoved(self, skillName: str):
		# noinspection SqlResolve
		self.DatabaseManager.delete(
			tableName=self.WIDGETS_TABLE,
			callerName=self.name,
			values={
				'skill': skillName
			}
		)

		tmp = self._widgets.copy()
		for wid, widget in tmp.items():
			if widget.skill == skillName:
				self._widgets.pop(wid, None)


	def skillDeactivated(self, skillName: str):
		self.skillRemoved(skillName)


	def getNextZIndex(self, pageId: int):
		# Build a list of widgets on this page
		widgets = list()
		for widget in self._widgets.values():
			if widget.page == pageId:
				widgets.insert(widget.z, widget)

		return len(widgets) + 1


	def saveWidgetPosition(self, widgetId: int, x: int, y: int) -> bool:  # NOSONAR
		widget: Widget = self._widgets.get(widgetId, None)

		if not widget:
			self.logWarning('Tried to save a widget position but widget doesn\'t exist')
			return False

		widget.x = x
		widget.y = y
		widget.saveToDB()
		return True


	def saveWidgetSize(self, widgetId: int, x: int, y: int, w: int, h: int) -> bool:  # NOSONAR
		widget: Widget = self._widgets.get(widgetId, None)

		if not widget:
			self.logWarning('Tried to save a widget size but widget doesn\'t exist')
			return False

		widget.x = x
		widget.y = y
		widget.size = f'{w}x{h}'
		widget.saveToDB()
		return True


	def saveWidgetParams(self, widgetId: int, params: dict) -> bool:  # NOSONAR
		widget: Widget = self._widgets.get(widgetId, None)

		if not widget:
			self.logWarning('Tried to save a widget params but widget doesn\'t exist')
			return False

		widget.params = params
		widget.saveToDB()
		return True


	@property
	def widgetTemplates(self) -> dict:
		return self._widgetTemplates


	@property
	def widgets(self) -> dict:
		return self._widgets


	@property
	def pages(self) -> dict:
		return self._pages
