from core.base.model.Manager import Manager
from core.device.model.Location import Location
from typing import Dict, List, Optional
import json

class LocationManager(Manager):

	TABLE = 'locations'
	DATABASE =  {
		TABLE: [
			'id INTEGER PRIMARY KEY',
			'name TEXT NOT NULL',
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
		self.logInfo(f'Loaded **{len(self._locations)}** location', plural='location')


	def getLocationWithName(self, name: str) -> Optional[Location]:
		for id, val in self._locations.items():
			if val.name == name:
				return val


	def loadLocations(self):
		for row in self.databaseFetch(tableName=self.TABLE, query='SELECT * FROM :__table__', method='all'):
			self._locations[row['id']] = Location(row)


	def addNewLocation(self, name: str = None) -> bool:
		loc = self.getLocationWithName(name)
		#todo check existing synonyms!
		if not loc:
			values = {'name': name}
			values['id'] = self.databaseInsert(tableName=self.TABLE, values=values)
			self._locations[values['id']] = Location(values)
			return self._locations[values['id']]
		else:
			raise Exception(f'Location {name} already exists')





	def deleteLocation(self, id: int) -> bool:
		self.DatabaseManager.delete(tableName=self.TABLE,
		                            callerName=self.name,
		                            values={'id': id})
		self._locations.pop(id, None)
		return True


	def addLocationSynonym(self, id: int, synonym: str):
		synlist = self._locations[id].addSynonym(synonym)
		self.DatabaseManager.update(tableName=self.TABLE,
		                            callerName=self.name,
		                            values={'synonyms': synlist},
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
			# unknown entry!
			if values['id'] == 'undefined':
				self.logError(f'unknown location updated! {values["name"]} reported without id.')
				continue
			# update display of location
			self._locations[values['id']].display = values['display']
			#todo check synonyms for new injection -> should happen while creating!
			self.DatabaseManager.update(tableName=self.TABLE,
			                            callerName=self.name,
			                            values={
				                            'display': values['display']
			                            },
			                            row=('id', values['id']))
			self.logInfo(data)
			for device in values['devices']:
				self.DeviceManager.updateDevice(device)
		pass

	def getLocation(self,id: int = None, room: str = None, siteID: str = None, deviceTypeID: int = None) -> Location:
		# room: a room name issued by the user
		# siteID: the current devices site NAME
		# deviceTypeID: only rooms with that type of device can be found - linked is allowed as well
		loc = None

		if id:
			loc = self.locations.get(id, None)
			if not loc:
				raise Exception(f'No location with id {id} found')
			return  loc

		if room:
			loc = self.getLocationWithName(name=room)
			if not loc:
				loc = self.LocationManager.addNewLocation(name=room)
			if loc:
				return loc

		return loc
		##todo implement location det. logic
		# 1a) check name vs locations
		# 1b) check name vs location synonyms
		# 2a) check siteID vs locations
		# 2b) check siteID vs synonyms
		# 3) try to get the location context sensitive
		# 4) check if there is only one room that has that type of device
		# if 1 or 2 provides names
		pass

	@property
	def locations(self) -> Dict[int, Location]:
		return self._locations


	def cleanRoomNameToSiteId(self, roomName: str) -> str:
		"""
		User might answer "in the living room" when asked for a room. In that case it should be turned into "living_room"
		:param roomName: str: original captured name
		:return: str: formated room name to site id
		"""

		parasites = self.LanguageManager.getStrings(key='inThe')

		for parasite in parasites:
			if parasite in roomName:
				roomName = roomName.replace(parasite, '')
				break

		return roomName.strip().replace(' ', '_')
