import json
from dataclasses import dataclass, field
import sqlite3
from flask import jsonify
import ast
from core.base.model.ProjectAliceObject import ProjectAliceObject

@dataclass
class Location(ProjectAliceObject):
	data: sqlite3.Row
	name: str = ''

	id: int = field(init=False)

	def __post_init__(self):
		self.id = self.data['id']
		self.name = self.data['name']
		if 'synonyms' in self.data.keys() and self.data['synonyms']:
			self.synonyms = ast.literal_eval(self.data['synonyms'])
		else:
			self.synonyms = list()
		if 'display' in self.data.keys() and self.data['display']:
			self.display = ast.literal_eval(self.data['display'])
		else:
			self.display = dict()


	def addSynonym(self,synonym: str):
		if synonym in self.synonyms:
			raise Exception(synonym,' already known')
		self.synonyms.append(synonym)
		return self.synonyms


	def deleteSynonym(self,synonym: str):
		if synonym not in self.synonyms:
			raise Exception(synonym,' unknown')
		self.synonyms.remove(synonym)
		return self.synonyms


	def toJson(self) -> str:
		return json.dumps({ self.name: {
			'id': self.id,
			'name': self.name,
			'synonyms': self.synonyms,
			'display': self.display
		}})

	def asJson(self):
		devices = {device.id: device.asJson() for device in self.DeviceManager.getDevicesByRoom(locationID=self.id)}
		return {
				'id'      : self.id,
				'name'    : self.name,
				'synonyms': self.synonyms,
				'display' : self.display,
				'devices' : devices
		}
