import json
from dataclasses import dataclass, field

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants


@dataclass
class Location(ProjectAliceObject):
	data: dict

	id: int = field(init=False)
	name: str = field(init=False)
	synonyms: set = field(default_factory=set)
	settings: dict = field(default_factory=dict)


	def __post_init__(self):
		self.id = self.data['id']
		self.name = self.data['name']
		self.synonyms = json.loads(self.data['synonyms'])
		self.settings = json.loads(self.data['settings'])


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
				'id'      : self.id,
				'name'    : self.name,
				'synonyms': self.synonyms,
				'settings': self.settings
			}
		})


	def toDict(self) -> dict:
		return {
			'id'      : self.id,
			'name'    : self.name,
			'synonyms': self.synonyms,
			'settings': self.settings
		}
