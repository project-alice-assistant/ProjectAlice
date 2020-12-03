import json
from typing import Dict, List, Optional

from core.base.model.Manager import Manager
from core.device.model.Construction import Construction
from core.device.model.Furniture import Furniture
from core.device.model.Location import Location
from core.dialog.model.DialogSession import DialogSession


class LocationManager(Manager):

	LOCATIONS_TABLE = 'locations'
	CONSTRUCTIONS_TABLE = 'constructions'
	FURNITURE_TABLE = 'furnitures'

	DATABASE = {
		LOCATIONS_TABLE: [
			'id INTEGER PRIMARY KEY', #NOSONAR
			'name TEXT NOT NULL',
			"synonyms TEXT NOT NULL DEFAULT '{}'",
			'parentLocation INTEGER NOT NULL DEFAULT 0',
			"settings TEXT NOT NULL DEFAULT '{}'"
		],
		CONSTRUCTIONS_TABLE: [
			'id INTEGER PRIMARY KEY',
			'parentLocation INTEGER',
			"settings TEXT DEFAULT '{}'"
		],
		FURNITURE_TABLE: [
			'id INTEGER PRIMARY KEY',
			'parentLocation INTEGER',
			"settings TEXT DEFAULT '{}'"
		]
	}


	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)

		self._locations: Dict[int, Location] = dict()
		self._constructions: Dict[int, Construction] = dict()
		self._furnitures: Dict[int, Furniture] = dict()


	def onStart(self):
		super().onStart()

		self.loadLocations()
		self.loadConstructions()
		self.loadFurnitures()

		self.logInfo(f'Loaded **{len(self._locations)}** location', plural='location')


	def loadLocations(self):
		for row in self.databaseFetch(tableName=self.LOCATIONS_TABLE, query='SELECT * FROM :__table__', method='all'): #NOSONAR
			self._locations[row['id']] = Location(self.Commons.dictFromRow(row))
			self.logInfo(f'Loaded location {row["id"]} - {row["name"]}')


	def loadConstructions(self):
		for row in self.databaseFetch(tableName=self.CONSTRUCTIONS_TABLE, query='SELECT * FROM :__table__', method='all'): #NOSONAR
			self._constructions[row['id']] = Construction(self.Commons.dictFromRow(row))


	def loadFurnitures(self):
		for row in self.databaseFetch(tableName=self.FURNITURE_TABLE, query='SELECT * FROM :__table__', method='all'): #NOSONAR
			self._furnitures[row['id']] = Furniture(self.Commons.dictFromRow(row))


	def addNewLocation(self, name: str = None, data: dict = None) -> Optional[Location]:
		if not name:
			name = data['name']

		if not name:
			self.logError('Cannot create a new location with empty name')
			return None

		if self.getLocationByName(name) or self.getLocationBySynonym(name=name):
			self.logWarning(f'Location with name or synonym **{name}** already exists')
			return None

		locationId = self.databaseInsert(
			tableName=self.LOCATIONS_TABLE,
			values={
				'name': name,
				'parentLocation': data['parentLocation']
			}
		)

		location = Location({
			'id': locationId,
			'name': name,
			'parentLocation': data['parentLocation'],
			'synonyms': json.dumps(list()),
			'settings': json.dumps({
				'x': data['x'],
				'y': data['y'],
				'z': data['z']
			})
		})

		self._locations[locationId] = location
		return location


	def deleteLocation(self, locId: int):
		self.DatabaseManager.delete(
			tableName=self.LOCATIONS_TABLE,
		    callerName=self.name,
		    values={
			    'id': locId
		    }
		)
		self._locations.pop(locId, None)

		self.DatabaseManager.delete(
			tableName=self.CONSTRUCTIONS_TABLE,
			callerName=self.name,
			values={
				'parentLocationId': locId
			}
		)

		for construction in self._constructions.copy().values():
			if construction.parentLocation == locId:
				self._constructions.pop(construction.id, None)


		self.DatabaseManager.delete(
			tableName=self.FURNITURE_TABLE,
			callerName=self.name,
			values={
				'parentLocationId': locId
			}
		)

		for furniture in self._furnitures.copy().values():
			if furniture.parentLocation == locId:
				self._furnitures.pop(furniture.id, None)


		self.DatabaseManager.delete(
			tableName=self.DeviceManager.DB_LINKS,
		    callerName=self.DeviceManager.name,
		    values={
			    'locationID': locId
		    }
		)


	def getLocationByName(self, name: str) -> Optional[Location]:
		return {location.name.lower(): location for location in self._locations.values()}.get(name.lower(), None)


	def getLocationBySynonym(self, name: str) -> Optional[Location]:
		for location in self._locations.values():
			if name.lower() in [synonym.lower() for synonym in location.synonyms]:
				return location
		return None


	def addLocationSynonym(self, locId: int, synonym: str):
		location = self.getLocationByName(synonym)
		if location:
			raise Exception(f'Synonym already used for {location.name}')
		synlist = self._locations[locId].addSynonym(synonym)
		self.DatabaseManager.update(tableName=self.LOCATIONS_TABLE,
		                            callerName=self.name,
		                            values={'synonyms': json.dumps(synlist)},
		                            row=('id', locId))


	def deleteLocationSynonym(self, locId: int, synonym: str):
		synlist = self._locations[locId].deleteSynonym(synonym)
		self.DatabaseManager.update(tableName=self.LOCATIONS_TABLE,
		                            callerName=self.name,
		                            values={
			                            'synonyms': json.dumps(synlist)
		                            },
		                            row=('id', locId))


	def getSettings(self, locId: int):
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
			self.DatabaseManager.update(tableName=self.LOCATIONS_TABLE,
			                            callerName=self.name,
			                            values={
				                            'display': json.dumps(values['display'])
			                            },
			                            row=('id', values['id']))
			for device in values['devices']:
				self.DeviceManager.updateDeviceDisplay(device)


	# noinspection PyUnusedLocal
	def getLocation(self, locId: int = None, location: str = None, siteId: str = None, deviceTypeId: int = None) -> Location:
		# todo implement location det. logic
		# 1a) check name vs locations - done
		# 1b) check name vs location synonyms - done
		# 2) get device for siteID, get main location of device - done
		# 3) try to get the location context sensitive
		# 4) check if there is only one room that has that type of device
		# if 1 or 2 provides names
		"""
		:param location: a location name issued by the user
		:param locId:
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

		if location:
			loc = self.getLocationByName(name=location)
			if not loc:
				loc = self.LocationManager.addNewLocation(name=location)
			if loc:
				return loc

		if siteId:
			loc = self.getLocationByName(name=siteId)
			if loc:
				return loc

			loc = self.DeviceManager.getDeviceByUID(uid=siteId).getMainLocation()
			if loc:
				return loc

		return loc


	def getLocationsForSession(self, sess: DialogSession, slotName: str = 'Location', noneIsEverywhere: bool = False) -> List[Location]:
		slotValues = [x.value['value'] for x in sess.slotsAsObjects.get(slotName, list())]
		if len(slotValues) == 0:
			if noneIsEverywhere:
				return [loc[1] for loc in self.locations.items()]
			else:
				device = self.DeviceManager.getDeviceByUID(uid=sess.siteId)
				if device:
					return [device.getMainLocation()]
				else:
					return list()
		else:
			return [self.getLocation(location=loc) for loc in slotValues]


	@property
	def locations(self) -> Dict[int, Location]:
		return self._locations


	@property
	def constructions(self) -> Dict[int, Construction]:
		return self._constructions


	@property
	def furnitures(self) -> Dict[int, Furniture]:
		return self._furnitures


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
