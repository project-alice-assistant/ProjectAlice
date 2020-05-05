import json
from dataclasses import dataclass, field

@dataclass
class Location:
	data: dict
	name: str = ''

	id: int = field(init=False)

	def __post_init__(self):
		self.id = self.data['id']
		self.name = self.data['name']
		self.synonyms = dict(self.data['synonyms'])
		self.coordinates = self.data['coordinates']


	def toJson(self) -> str:
		return json.dumps({
			'id': self.id,
			'name': self.name,
			'synonyms': self.synonyms,
			'coordinates': self.coordinates
		})
