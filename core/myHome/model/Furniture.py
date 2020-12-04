import json
import math
from dataclasses import dataclass, field

from core.base.model.ProjectAliceObject import ProjectAliceObject


@dataclass
class Furniture(ProjectAliceObject):
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
			'w': 25,
			'h': 25,
			'r': 0,
			't': ''
		}
		self.settings = {**settings, **self.settings}

		if self.id == -1:
			self.saveToDB()


	# noinspection SqlResolve
	def saveToDB(self):
		if self.id != -1:
			self.DatabaseManager.replace(
				tableName=self.LocationManager.FURNITURE_TABLE,
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
				tableName=self.LocationManager.FURNITURE_TABLE,
				callerName=self.LocationManager.name,
				values={
					'parentLocation': self.parentLocation,
					'settings'      : json.dumps(self.settings)
				}
			)

			self.id = constructionId


	def updateSettings(self, settings: dict):
		if 'x' in settings:
			settings['x'] = math.ceil(settings['x'] / 5) * 5
		if 'y' in settings:
			settings['y'] = math.ceil(settings['y'] / 5) * 5
		if 'w' in settings:
			settings['w'] = math.ceil(settings['w'] / 5) * 5
		if 'h' in settings:
			settings['h'] = math.ceil(settings['y'] / 5) * 5

		self.settings = {**self.settings, **settings}


	def toDict(self) -> dict:
		return {
			'id'            : self.id,
			'parentLocation': self.parentLocation,
			'settings'      : self.settings
		}
