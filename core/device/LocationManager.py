from core.base.model.Manager import Manager
from core.device.model.Location import Location
from typing import Dict, List, Optional
import json

class LocationManager(Manager):

	TABLE = 'locations'
	DATABASE =  {
		TABLE: [
			'id INTEGER PRIMARY KEY',
			'name TEXT',
			'synonyms TEXT',
			'display TEXT'
		]
	}


	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)
		self._locations: Dict[str, Location] = dict()


	def onStart(self):
		super().onStart()

		self.loadLocations()
		self.logInfo(f'Loaded **{len(self._locations)}** room', plural='rooms')


	def getLocationWithName(self, name: str):
		for id, val in self._locations.items():
			if val.name == name:
				return val


	def loadLocations(self):
		for row in self.databaseFetch(tableName=self.TABLE, query='SELECT * FROM :__table__', method='all'):
			self._locations[row['id']] = Location(row)


	def addNewLocation(self, name: str = None) -> bool:
		# TODO check first if name is already existing!
		values = {'name': name}
		values['id'] = self.databaseInsert(tableName=self.TABLE, query='INSERT INTO :__table__ (name) VALUES (:name)', values=values)
		self._locations[values['id']] = Location(values)
		return self._locations[values['id']]


	def deleteLocation(self, id: int) -> bool:
		self.DatabaseManager.delete(tableName=self.TABLE,
		                            callerName=self.name,
		                            query='DELETE FROM :__table__ WHERE id = :id',
		                            values={'id': id})
		self._locations.pop(id, None)
		return True


	def addLocationSynonym(self, id: int, synonym: str):
		synlist = self._locations[id].addSynonym(synonym)
		self.DatabaseManager.update(tableName=self.TABLE,
		                            callerName=self.name,
		                            values={
			                            'synonyms': synlist
		                            },
		                            row=('id', id))


	def deleteLocationSynonym(self, id: int, synonym: str):
		synlist = self._locations[id].deleteSynonym(synonym)
		self.DatabaseManager.update(tableName=self.TABLE,
		                            callerName=self.name,
		                            values={
			                            'synonyms': synlist
		                            },
		                            row=('id', id))


	def getSettings(self, id: int):
		return self._locations[id].synonyms

	def updateLocations(self, data: Dict):
		for room, values in data.items():
			# new entry! TODO should not happen anymore? Adding happened before!
			if values['id'] == 'undefined':
				values['id'] = self.addNewLocation(values['name']).id
			self._locations[values['id']].display = values['display']
			#todo update devices
			#todo check synonyms for new injection
			self.DatabaseManager.update(tableName=self.TABLE,
			                            callerName=self.name,
			                            values={
				                            'display': values['display']
			                            },
			                            row=('id', values['id']))
		pass
