from core.base.model.Manager import Manager
from core.base.model.Widget import Widget


class WidgetManager(Manager):
	DATABASE = {
		'widgets'    : [
			'skill TEXT NOT NULL UNIQUE',
			'name TEXT NOT NULL UNIQUE',
			'posx INTEGER NOT NULL',
			'posy INTEGER NOT NULL',
			'height INTEGER NOT NULL',
			'width INTEGER NOT NULL',
			'state TEXT NOT NULL',
			'options TEXT NOT NULL',
			'custStyle TEXT NOT NULL',
			'zindex INTEGER',
			'parent TEXT',
			'page INTEGER NOT NULL DEFAULT 0'
		],
		'widgetPages': [
			'id INTEGER PRIMARY KEY',
			'icon TEXT NOT NULL',
			'position INTEGER NOT NULL UNIQUE'
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
			if widget['skill'] not in self._widgetTemplates.values or \
					widget['name'] not in allTemplates:

				self.logInfo(f'Widget **{widget["name"]}** is deprecated, removing')
				# noinspection SqlResolve
				self.DatabaseManager.delete(
					tableName='widgets',
					callerName=self.SkillManager.name,
					query='DELETE FROM :__table__ WHERE skill = :skill AND name = :name',
					values={
						'parent': widget['skill'],
						'name'  : widget['name']
					}
				)
				continue

			# self._widgetInstance[SKILLNAME][WIDGETNAME][LIST OF INSTANCES]
			self._widgetInstances.setdefault(widget['skill'], dict()).setdefault(widget['name'], list())
			self._widgetInstances[widget['skill']][widget['name']].append(Widget(widget))

		self.logInfo(f'Loaded **{count}** widget template from {len(self._widgetTemplates)} skill', plural=['template', 'skill'])
		self.logInfo(f'Loaded {len(self._widgetInstances)} active widget', plural='widget')


	def loadPages(self):
		data = self.DatabaseManager.fetch(
			tableName='widgetPages',
			query='SELECT * FROM :__table__',
			callerName=self.name,
			method='all'
		)
		if data:
			self._pages = {row['id']: row for row in data}
		else:
			# Insert default page
			self.DatabaseManager.insert(
				tableName='widgetPages',
				callerName=self.name,
				values={
					'icon'    : 'fas fa-biohazard',
					'position': 0
				}
			)
			return self.loadPages()

		self.logInfo(f'Loaded **{len(self._pages)}** page', plural='page')


	def skillRemoved(self, skillName: str):
		# noinspection SqlResolve
		self.DatabaseManager.delete(
			tableName='widgets',
			callerName=self.name,
			query='DELETE FROM :__table__ WHERE skill = :skill',
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


	def getAvailableWidgets(self) -> dict:
		# TODO
		return {widget: dict() for widget in self._widgetTemplates.items()}
