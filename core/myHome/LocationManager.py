from typing import Dict, List, Optional

from core.base.model.Manager import Manager
from core.myHome.model.Construction import Construction
from core.myHome.model.Furniture import Furniture
from core.myHome.model.Location import Location
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
		for row in self.databaseFetch(tableName=self.LOCATIONS_TABLE, method='all'): #NOSONAR
			self._locations[row['id']] = Location(self.Commons.dictFromRow(row))
			self.logInfo(f'Loaded location **{row["name"]}**')


	def loadConstructions(self):
		for row in self.databaseFetch(tableName=self.CONSTRUCTIONS_TABLE, method='all'): #NOSONAR
			self._constructions[row['id']] = Construction(self.Commons.dictFromRow(row))


	def loadFurnitures(self):
		for row in self.databaseFetch(tableName=self.FURNITURE_TABLE, method='all'): #NOSONAR
			self._furnitures[row['id']] = Furniture(self.Commons.dictFromRow(row))


	def addNewFurniture(self, data: dict) -> Optional[Furniture]:
		furniture = Furniture(data)
		self._furnitures[furniture.id] = furniture

		return furniture


	def deleteFurniture(self, furId: int):
		self.DatabaseManager.delete(
			tableName=self.FURNITURE_TABLE,
		    callerName=self.name,
		    values={
			    'id': furId
		    }
		)
		self._furnitures.pop(furId, None)


	def updateFurniture(self, furId: int, data: dict) -> Furniture:
		furniture = self._furnitures.get(furId, None)
		if not furniture:
			raise Exception(f"Cannot update furniture, furniture with id **{furId}** doesn't exist")

		if 'parentLocation' in data:
			furniture.parentLocation = data['parentLocation']

		if 'settings' in data:
			furniture.updateSettings(data['settings'])

		furniture.saveToDB()
		return furniture


	def getFurnitureSettings(self, furId: int) -> dict:
		furniture = self._furnitures.get(furId, None)
		if not furniture:
			raise Exception(f"Cannot retrieve settings, furniture with id **{furId}** doesn't exist")

		return furniture.settings


	def addNewLocation(self, data: dict) -> Optional[Location]:
		name = data['name']

		if not name:
			self.logError('Cannot create a new location with empty name')
			return None

		if self.getLocationByName(name) or self.getLocationBySynonym(name=name):
			self.logWarning(f'Location with name or synonym **{name}** already exists')
			return None

		location = Location(data)
		self._locations[location.id] = location

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
				'parentLocation': locId
			}
		)

		for construction in self._constructions.copy().values():
			if construction.parentLocation == locId:
				self._constructions.pop(construction.id, None)


		self.DatabaseManager.delete(
			tableName=self.FURNITURE_TABLE,
			callerName=self.name,
			values={
				'parentLocation': locId
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
		location = self.getLocationBySynonym(synonym)
		if location:
			raise Exception(f'Synonym already used for {location.name}')

		location = self._locations.get(locId, None)
		if not location:
			raise Exception(f"Cannot add synonym, location with id **{locId}** doesn't exist")

		location.addSynonym(synonym)
		location.saveToDB()


	def deleteLocationSynonym(self, locId: int, synonym: str):
		location = self._locations.get(locId, None)
		if not location:
			raise Exception(f"Cannot remove synonym, location with id **{locId}** doesn't exist")

		location.deleteSynonym(synonym)
		location.saveToDB()


	def getLocationSettings(self, locId: int) -> dict:
		location = self._locations.get(locId, None)
		if not location:
			raise Exception(f"Cannot retrieve settings, location with id **{locId}** doesn't exist")

		return location.settings


	def updateLocation(self, locId: int, data: dict) -> Location:
		location = self._locations.get(locId, None)
		if not location:
			raise Exception(f"Cannot update location, location with id **{locId}** doesn't exist")

		if 'name' in data:
			location.name = data['name']

		if 'parentLocation' in data:
			location.parentLocation = data['parentLocation']

		if 'synonyms' in data:
			location.updatesynonyms(set(data['synonyms']))

		if 'settings' in data:
			location.updateSettings(data['settings'])

		location.saveToDB()
		return location


	# noinspection PyUnusedLocal
	def getLocation(self, locId: int = None, locationName: str = None, locationSynonym: str = None, siteId: str = None, deviceTypeId: int = None) -> Optional[Location]:
		# todo implement location det. logic
		# 1a) check name vs locations - done
		# 1b) check name vs location synonyms - done
		# 2) get device for siteID, get main location of device - done
		# 3) try to get the location context sensitive
		# 4) check if there is only one room that has that type of device
		# if 1 or 2 provides names
		"""
		:param locationName: a location name issued by the user
		:param locationSynonym: the name could be a synonym
		:param locId:
		:param siteId: the current devices site NAME
		:param deviceTypeId: only rooms with that type of device can be found - linked is allowed as well
		:return: Location
		"""

		if locId:
			loc = self._locations.get(locId, None)
			if not loc:
				raise Exception(f'No location with id {locId} found')

			return loc

		if locationName:
			loc = self.getLocationByName(name=locationName)
			if not loc and locationSynonym:
				loc = self.getLocationBySynonym(locationSynonym)

			return loc

		if siteId:
			loc = self.getLocationByName(name=siteId)
			if loc:
				return loc

			return self.DeviceManager.getDeviceByUID(uid=siteId).getMainLocation()

		return None


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
