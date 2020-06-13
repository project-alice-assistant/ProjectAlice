import json
from typing import Dict, Optional

from core.base.model.Manager import Manager
from core.device.model.Location import Location


class LocationManager(Manager):
	TABLE = 'locations'
	DATABASE = {
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
		for val in self._locations.values():
			if val.name == name:
				return val


	def loadLocations(self):
		for row in self.databaseFetch(tableName=self.TABLE, query='SELECT * FROM :__table__', method='all'):
			self._locations[row['id']] = Location(row)


	def addNewLocation(self, name: str = None) -> Location:
		loc = self.getLocationWithName(name)
		# todo check existing synonyms!
		if not loc:
			values = {'name': name}
			values['id'] = self.databaseInsert(tableName=self.TABLE, values=values)
			# noinspection PyTypeChecker
			self._locations[values['id']] = Location(values)
			return self._locations[values['id']]
		else:
			raise Exception(f'Location {name} already exists')


	def deleteLocation(self, locId: str) -> bool:
		self.DatabaseManager.delete(tableName=self.TABLE,
		                            callerName=self.name,
		                            values={'id': locId})
		self._locations.pop(locId, None)
		return True


	def addLocationSynonym(self, locId: str, synonym: str):
		synlist = self._locations[locId].addSynonym(synonym)
		self.DatabaseManager.update(tableName=self.TABLE,
		                            callerName=self.name,
		                            values={'synonyms': synlist},
		                            row=('id', locId))


	def deleteLocationSynonym(self, locId: str, synonym: str):
		synlist = self._locations[locId].deleteSynonym(synonym)
		self.DatabaseManager.update(tableName=self.TABLE,
		                            callerName=self.name,
		                            values={
			                            'synonyms': synlist
		                            },
		                            row=('id', locId))


	def getSettings(self, locId: str):
		return self._locations[locId].synonyms


	def updateLocations(self, data: Dict):
		for room, values in data.items():
			# unknown entry!
			if values['id'] == 'undefined':
				self.logError(f'Unknown location updated! {values["name"]} reported without id.')
				continue
			# update display of location
			self._locations[values['id']].display = values['display']
			# todo check synonyms for new injection -> should happen while creating!
			self.DatabaseManager.update(tableName=self.TABLE,
			                            callerName=self.name,
			                            values={
				                            'display': values['display']
			                            },
			                            row=('id', values['id']))
			self.logInfo(json.dumps(data))
			for device in values['devices']:
				self.DeviceManager.updateDevice(device)


	# noinspection PyUnusedLocal
	def getLocation(self, locId: str = None, room: str = None, siteId: str = None, deviceTypeId: int = None) -> Location:
		# TODO siteId is not in use
		"""
		:param locId:
		:param room: a room name issued by the user
		:param siteId: the current devices site NAME
		:param deviceTypeId: only rooms with that type of device can be found - linked is allowed as well
		:return: Location
		"""

		loc = None

		if locId:
			loc = self._locations.get(locId, None)
			if not loc:
				raise Exception(f'No location with id {locId} found')
			return loc

		if room:
			loc = self.getLocationWithName(name=room)
			if not loc:
				loc = self.LocationManager.addNewLocation(name=room)
			if loc:
				return loc

		return loc


	# todo implement location det. logic
	# 1a) check name vs locations - done
	# 1b) check name vs location synonyms
	# 2a) check siteID vs locations
	# 2b) check siteID vs synonyms
	# 3) try to get the location context sensitive
	# 4) check if there is only one room that has that type of device
	# if 1 or 2 provides names

	@property
	def locations(self) -> Dict[str, Location]:
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
