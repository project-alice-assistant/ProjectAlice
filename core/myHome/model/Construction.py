import json
from dataclasses import dataclass, field

from core.base.model.ProjectAliceObject import ProjectAliceObject


@dataclass
class Construction(ProjectAliceObject):
	data: dict

	id: int = field(init=False)
	parentLocation: int = field(init=False)
	settings: dict = field(init=False)


	def __post_init__(self):
		self.id = self.data.get('id', -1)
		self.parentLocation = self.data['parentLocation']
		self.settings = json.loads(self.data.get('settings', '{}')) if isinstance(self.data.get('settings', '{}'), str) else self.data.get('settings', dict)

		settings = {
			'x': 0,
			'y': 0,
			'z': 0,
			'w': 10,
			'h': 50,
			'r': 0,
			'c': '',
			'b': ''
		}

		self.settings = {**settings, **self.settings}

		if self.id == -1:
			self.saveToDB()


	# noinspection SqlResolve
	def saveToDB(self):
		if self.id != -1:
			self.DatabaseManager.replace(
				tableName=self.LocationManager.CONSTRUCTIONS_TABLE,
				query='REPLACE INTO :__table__ (id, parentLocation, settings) VALUES (:id, :parentLocation, :settings)',
				callerName=self.LocationManager.name,
				values={
					'id'            : self.id,
					'parentLocation': self.parentLocation,
					'settings'      : json.dumps(self.settings)
				}
			)
		else:
			constructionId = self.DatabaseManager.insert(
				tableName=self.LocationManager.CONSTRUCTIONS_TABLE,
				callerName=self.LocationManager.name,
				values={
					'parentLocation': self.parentLocation,
					'settings'      : json.dumps(self.settings)
				}
			)

			self.id = constructionId


	def updateSettings(self, settings: dict):
		self.settings = {**self.settings, **settings}


	def toDict(self) -> dict:
		return {
			'id'            : self.id,
			'parentLocation': self.parentLocation,
			'settings'      : self.settings
		}
