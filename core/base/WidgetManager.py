import importlib
from typing import Optional

from core.base.model.Manager import Manager
from core.base.model.Widget import Widget
from core.base.model.WidgetPage import WidgetPage


class WidgetManager(Manager):
	DEFAULT_ICON = 'fas fa-biohazard'

	DATABASE = {
		'widgets'    : [
			'id INTEGER PRIMARY KEY',
			'skill TEXT NOT NULL UNIQUE',
			'name TEXT NOT NULL UNIQUE',
			"params TEXT NOT NULL DEFAULT '{}'",
			"settings TEXT NOT NULL DEFAULT '{}'",
			'page INTEGER NOT NULL DEFAULT 0'
		],
		'widgetPages': [
			'id INTEGER PRIMARY KEY',
			'icon TEXT NOT NULL',
			'position INTEGER NOT NULL'
		]
	}


	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)
		self._widgetTemplates = dict()
		self._widgetInstances = dict()
		self._pages = dict()
		self._widgetsByIndex = dict()


	def onStart(self):
		super().onStart()
		self.loadPages()
		self.loadWidgets()
		self.sortWidgetZIndexes()


	def loadWidgets(self):
		count = 0
		for skill in self.SkillManager.allSkills.values():
			if not skill.widgets:
				continue

			count += len(skill.widgets)
			self._widgetTemplates[skill.name] = skill.widgets

		allTemplates = list()
		for widgets in self._widgetTemplates.values():
			allTemplates += widgets

		# Cleanup possible deprecated widgets
		data = self.DatabaseManager.fetch(
			tableName='widgets',
			query='SELECT * FROM :__table__',
			callerName=self.name,
			method='all'
		)

		for widget in data:
			if widget['skill'] not in self._widgetTemplates or widget['name'] not in allTemplates:

				self.logInfo(f'Widget **{widget["name"]}** is deprecated, removing')
				# noinspection SqlResolve
				self.DatabaseManager.delete(
					tableName='widgets',
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

			# self._widgetInstance[SKILLNAME][WIDGETNAME][LIST OF INSTANCES]
			self._widgetInstances.setdefault(widget['skill'], dict()).setdefault(widget['name'], list())
			self._widgetInstances[widget['skill']][widget['name']].append(instance)

		self.logInfo(f'Loaded **{count}** template from {len(self._widgetTemplates)} skill', plural=['template', 'skill'])
		self.logInfo(f'Loaded {len(self._widgetInstances)} active widget', plural='widget')


	def instanciateWidget(self, widgetData: dict) -> Optional[Widget]:
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

		self._widgetInstances.setdefault(skillName, dict()).setdefault(widgetName, list())
		self._widgetInstances[skillName][widgetName].append(instance)

		instance.saveToDB()
		return instance


	def loadPages(self):
		data = self.DatabaseManager.fetch(
			tableName='widgetPages',
			query='SELECT * FROM :__table__',
			callerName=self.name,
			method='all'
		)
		if data:
			self._pages = {row['id']: WidgetPage(row) for row in data}
		else:
			# Insert default page
			self.DatabaseManager.insert(
				tableName='widgetPages',
				callerName=self.name,
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

			pageId = self.DatabaseManager.insert(
				tableName='widgetPages',
				callerName=self.name,
				values={
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
			tableName='widgetPages',
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
				tableName='widgetPages',
				callerName=self.name,
				values={
					'position': page.position
				},
				row=('id', pid)
			)
		self._pages.pop(pageId, None)

		self.DatabaseManager.delete(
			tableName='widgetPages',
			callerName=self.name,
			values={
				'id': pageId
			}
		)


	# TODO Remove widgets instances


	def removeWidget(self, widgetId: int):
		self.DatabaseManager.delete(
			tableName='widgets',
			callerName=self.name,
			values={
				'id': widgetId
			}
		)


	def skillRemoved(self, skillName: str):
		# noinspection SqlResolve
		self.DatabaseManager.delete(
			tableName='widgets',
			callerName=self.name,
			values={'skill': skillName}
		)


	def skillDeactivated(self, skillName: str):
		self.DatabaseManager.update(
			tableName='widgets',
			callerName=self.name,
			values={
				'state' : 0,
				'posx'  : 0,
				'posy'  : 0,
				'zindex': -1
			},
			row=('skill', skillName)
		)


	def sortWidgetZIndexes(self):
		# TODO rework for multi page support, z indexes can be same
		return


	# Create a list of skills with their z index as key
	# self._widgetsByIndex = dict()
	# for skillName, widgetList in self._widgetTemplates.items():
	# 	for widget in widgetList.values():
	# 		if widget.state != 1:
	# 			continue
	#
	# 		if int(widget.zindex) not in self._widgetsByIndex:
	# 			self._widgetsByIndex[int(widget.zindex)] = widget
	# 		else:
	# 			i = 1000
	# 			while True:
	# 				if i not in self._widgetsByIndex:
	# 					self._widgetsByIndex[i] = widget
	# 					break
	# 				i += 1
	#
	# # Rewrite a logical zindex flow
	# for i, widget in enumerate(self._widgetsByIndex.values()):
	# 	widget.zindex = i
	# 	widget.saveToDB()


	def nextZIndex(self) -> int:
		return len(self._widgetsByIndex)


	@property
	def widgetTemplates(self) -> dict:
		return self._widgetTemplates


	@property
	def widgetInstances(self) -> dict:
		return self._widgetInstances


	@property
	def pages(self) -> dict:
		return self._pages
