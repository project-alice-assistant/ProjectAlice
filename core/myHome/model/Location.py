import json
from dataclasses import dataclass, field

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.util.Decorators import deprecated


@dataclass
class Location(ProjectAliceObject):
	data: dict

	id: int = field(init=False)
	name: str = field(init=False)
	parentLocation: int = field(init=False)
	synonyms: set = field(default_factory=set)
	settings: dict = field(default_factory=dict)


	def __post_init__(self):
		self.id = self.data.get('id', -1)
		self.name = self.data['name']
		self.parentLocation = self.data['parentLocation']
		self.synonyms = set(json.loads(self.data.get('synonyms', '{}')))
		self.settings = json.loads(self.data.get('settings', '{}')) if isinstance(self.data.get('settings', '{}'), str) else self.data.get('settings', dict)

		settings = {
			'x': 0,
			'y': 0,
			'z': len(self.LocationManager.locations),
			'w': 150,
			'h': 150,
			'r': 0,
			't': '',
			'b': ''
		}
		self.settings = {**settings, **self.settings}

		if self.id == -1:
			self.saveToDB()


	# noinspection SqlResolve
	def saveToDB(self):
		if self.id != -1:
			self.DatabaseManager.replace(
				tableName=self.LocationManager.LOCATIONS_TABLE,
				query='REPLACE INTO :__table__ (id, name, parentLocation, synonyms, settings) VALUES (:id, :name, :parentLocation, :synonyms, :settings)',
				callerName=self.LocationManager.name,
				values={
					'id'            : self.id,
					'name'          : self.name,
					'parentLocation': self.parentLocation,
					'synonyms'      : json.dumps(list(self.synonyms)),
					'settings'      : json.dumps(self.settings)
				}
			)
		else:
			locationId = self.DatabaseManager.insert(
				tableName=self.LocationManager.LOCATIONS_TABLE,
				callerName=self.LocationManager.name,
				values={
					'name'          : self.name,
					'parentLocation': self.parentLocation,
					'synonyms'      : json.dumps(list(self.synonyms)),
					'settings'      : json.dumps(self.settings)
				}
			)

			self.id = locationId


	def updateSettings(self, settings: dict):
		self.settings = {**self.settings, **settings}


	def updatesynonyms(self, synonyms):
		self.synonyms = {*self.synonyms, *synonyms}


	@deprecated
	def getSaveName(self) -> str:
		return self.name.replace(' ', '_')


	def changeName(self, newName: str):
		self.name = newName
		self.DatabaseManager.update(
			tableName=self.LocationManager.LOCATIONS_TABLE,
			callerName=self.LocationManager.name,
			values={'name': newName},
			row=('id', self.id)
		)


	def addSynonym(self, synonym: str):
		self.synonyms.add(synonym)


	def deleteSynonym(self, synonym: str):
		try:
			self.synonyms.remove(synonym)
		except:
			raise Exception(synonym, constants.UNKNOWN)


	def toJson(self) -> str:
		return json.dumps({
			self.name: {
				'id'            : self.id,
				'name'          : self.name,
				'parentLocation': self.parentLocation,
				'synonyms'      : list(self.synonyms),
				'settings'      : self.settings
			}
		})


	def toDict(self) -> dict:
		return {
			'id'            : self.id,
			'name'          : self.name,
			'parentLocation': self.parentLocation,
			'synonyms'      : list(self.synonyms),
			'settings'      : self.settings
		}
