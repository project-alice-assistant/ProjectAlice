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
		self.id = self.data['id']
		self.name = self.data['name']
		self.settings = json.loads(self.data['settings'])

		if not self.settings:
			self.settings = {
				'x': 0,
				'y': 0,
				'z': 0,
				'w': 10,
				'h': 50,
				'rotation': 0,
				'color': ''
			}


	def toDict(self) -> dict:
		return {
			'id': self.id,
			'parentLocation': self.parentLocation,
			'settings': self.settings
		}
