from dataclasses import dataclass


@dataclass
class WidgetPage:
	data: dict
	id: int = 0
	icon: str = ''
	position: int = 0


	def __post_init__(self):
		self.id = self.data['id']
		self.icon = self.data['icon']
		self.position = self.data['position']


	def toDict(self) -> dict:
		return {
			'id'      : self.id,
			'icon'    : self.icon,
			'position': self.position
		}
