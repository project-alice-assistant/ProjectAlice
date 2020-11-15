from core.base.model.Manager import Manager


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
			'parent TEXT'
		],
		'widgetPages': [
			'id INTEGER PRIMARY KEY',
			'icon TEXT NOT NULL',
			'position INTEGER NOT NULL UNIQUE'
		]
	}


	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)
		self._widgets = dict()
		self._widgetsByIndex = dict()

		self.sortWidgetZIndexes()


	def skillRemoved(self, skillName: str):
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
		# Create a list of skills with their z index as key
		self._widgetsByIndex = dict()
		for skillName, widgetList in self._widgets.items():
			for widget in widgetList.values():
				if widget.state != 1:
					continue

				if int(widget.zindex) not in self._widgetsByIndex:
					self._widgetsByIndex[int(widget.zindex)] = widget
				else:
					i = 1000
					while True:
						if i not in self._widgetsByIndex:
							self._widgetsByIndex[i] = widget
							break
						i += 1

		# Rewrite a logical zindex flow
		for i, widget in enumerate(self._widgetsByIndex.values()):
			widget.zindex = i
			widget.saveToDB()


	def nextZIndex(self) -> int:
		return len(self._widgetsByIndex)


	@property
	def widgets(self) -> dict:
		return self._widgets
