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
