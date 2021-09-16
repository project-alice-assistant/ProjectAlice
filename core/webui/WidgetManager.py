#  Copyright (c) 2021
#
#  This file, WidgetManager.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:49 CEST

import importlib
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Union

from core.base.model.Manager import Manager
from core.webui.model.Widget import Widget
from core.webui.model.WidgetPage import WidgetPage


class WidgetManager(Manager):
	DEFAULT_ICON = 'fas fa-biohazard'

	WIDGETS_TABLE = 'activeWidgets'
	WIDGET_PAGES_TABLE = 'widgetPages'

	DATABASE = {
		WIDGETS_TABLE              : [
			'id INTEGER PRIMARY KEY',  # NOSONAR
			'skill TEXT NOT NULL',
			'name TEXT NOT NULL',
			"settings TEXT NOT NULL DEFAULT '{}'",
			"configs TEXT NOT NULL DEFAULT '{}'",
			'page INTEGER NOT NULL DEFAULT 0'
		],
		WIDGET_PAGES_TABLE         : [
			'id INTEGER PRIMARY KEY',
			'icon TEXT NOT NULL',
			'position INTEGER NOT NULL'
		]
	}


	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)
		self._widgetTemplates: Dict[str, List[Path]] = dict()
		self._widgets: Dict[int, Widget] = dict()
		self._pages = dict()
		self._widgetsByIndex = dict()


	def onStart(self):
		super().onStart()
		self.loadPages()
		self.loadWidgets()
		self.getNextZIndex(1)


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
		rows = self.databaseFetch(tableName=self.WIDGETS_TABLE)

		for widget in rows:
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
			self.logWarning(f'Skill {widgetData["skill"]} for widget {widgetData["name"]} is not instantiated, skipping widget')
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
			self.logWarning(f'Tried to add widget **{widgetName}** from skill **{skillName}** to page id **{pageId}** but the page does not exist')
			return None

		instance = self.instanciateWidget({
			'skill'   : skillName,
			'name'    : widgetName,
			'settings': '{}',
			'configs' : '{}',
			'page'    : pageId
		})

		self._widgets[instance.id] = instance

		return instance


	def loadPages(self):
		rows = self.databaseFetch(tableName=self.WIDGET_PAGES_TABLE)
		if rows:
			self._pages = {row['id']: WidgetPage(row) for row in rows}
		else:
			# Insert default page
			self.databaseInsert(
				tableName=self.WIDGET_PAGES_TABLE,
				values={
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
			self.logWarning('Tried to save a widget position but widget does not exist')
			return False

		widget.x = x
		widget.y = y
		widget.saveToDB()
		return True


	def saveWidgetSize(self, widgetId: int, x: int, y: int, w: int, h: int) -> bool:  # NOSONAR
		widget: Widget = self._widgets.get(widgetId, None)

		if not widget:
			self.logWarning('Tried to save a widget size but widget does not exist')
			return False

		widget.x = x
		widget.y = y
		widget.w = w
		widget.h = h
		widget.saveToDB()
		return True


	def saveWidgetSettings(self, widgetId: int, settings: dict) -> bool:  # NOSONAR
		widget: Widget = self._widgets.get(widgetId, None)

		if not widget:
			self.logWarning('Tried to save widget settings but widget does not exist')
			return False

		widget.settings = settings
		widget.saveToDB()
		return True


	def saveWidgetConfigs(self, widgetId: int, configs: dict) -> bool:  # NOSONAR
		widget: Widget = self._widgets.get(widgetId, None)

		if not widget:
			self.logWarning('Tried to save widget settings but widget does not exist')
			return False

		widget._configs = configs
		widget.saveToDB()
		return True


	def getWidgetInstance(self, widgetId: int) -> Optional[Widget]:
		return self._widgets.get(widgetId, None)


	@property
	def widgetTemplates(self) -> dict:
		return self._widgetTemplates


	@property
	def widgets(self) -> dict:
		return self._widgets


	@property
	def pages(self) -> dict:
		return self._pages
