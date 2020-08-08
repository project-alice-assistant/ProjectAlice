import ast
import json
import sqlite3
from dataclasses import dataclass, field

from core.base.model.ProjectAliceObject import ProjectAliceObject


@dataclass
class Location(ProjectAliceObject):
	data: sqlite3.Row
	name: str = ''

	id: int = field(init=False)


	def __post_init__(self):
		self.id = self.data['id']
		self.name = self.data['name']
		self.synonyms = list()
		if 'synonyms' in self.data.keys() and self.data['synonyms']:
			self.synonyms = ast.literal_eval(self.data['synonyms'])
		self.display = dict()
		if 'display' in self.data.keys() and self.data['display']:
			self.display = ast.literal_eval(self.data['display'])


	def getSaveName(self) -> str:
		return self.name.replace(' ', '_')


	def addSynonym(self, synonym: str) -> list:
		if synonym in self.synonyms:
			raise Exception(synonym, ' already known')
		self.synonyms.append(synonym)
		return self.synonyms


	def deleteSynonym(self, synonym: str) -> list:
		if synonym not in self.synonyms:
			raise Exception(synonym, ' unknown')
		self.synonyms.remove(synonym)
		return self.synonyms


	def toJson(self) -> str:
		return json.dumps({
			self.name: {
				'id'      : self.id,
				'name'    : self.name,
				'synonyms': self.synonyms,
				'display' : self.display
			}
		})


	def asJson(self) -> dict:
		devices = {device.id: device.asJson() for device in self.DeviceManager.getDevicesByLocation(locationID=self.id, withLinks=False)}
		return {
			'id'      : self.id,
			'name'    : self.name,
			'synonyms': self.synonyms,
			'display' : self.display,
			'devices' : devices
		}
