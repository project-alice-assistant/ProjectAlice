#  Copyright (c) 2021
#
#  This file, Location.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:47 CEST

import json
from dataclasses import dataclass, field

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants
from core.util.Decorators import deprecated


@dataclass
class Location(ProjectAliceObject):
	data: dict

	id: int = field(init=False)
	name: str = field(init=False)
	parentLocation: int = field(init=False)
	synonyms: set = field(default_factory=set)
	settings: dict = field(default_factory=dict)


	def __post_init__(self):
		self.id = self.data.get('id', -1)
		self.name = self.data['name']
		self.parentLocation = self.data['parentLocation']
		self.synonyms = set(json.loads(self.data.get('synonyms', '{}')))
		self.settings = json.loads(self.data.get('settings', '{}')) if isinstance(self.data.get('settings', '{}'), str) else self.data.get('settings', dict)

		settings = {
			'x': 50000,
			'y': 50000,
			'z': len(self.LocationManager.locations),
			'w': 150,
			'h': 150,
			'r': 0,
			't': '',
			'b': ''
		}
		self.settings = {**settings, **self.settings}

		if self.id == -1:
			self.saveToDB()


	# noinspection SqlResolve
	def saveToDB(self):
		if self.id != -1:
			self.DatabaseManager.replace(
				tableName=self.LocationManager.LOCATIONS_TABLE,
				query='REPLACE INTO :__table__ (id, name, parentLocation, synonyms, settings) VALUES (:id, :name, :parentLocation, :synonyms, :settings)',
				callerName=self.LocationManager.name,
				values={
					'id'            : self.id,
					'name'          : self.name,
					'parentLocation': self.parentLocation,
					'synonyms'      : json.dumps(list(self.synonyms)),
					'settings'      : json.dumps(self.settings)
				}
			)
		else:
			locationId = self.DatabaseManager.insert(
				tableName=self.LocationManager.LOCATIONS_TABLE,
				callerName=self.LocationManager.name,
				values={
					'name'          : self.name,
					'parentLocation': self.parentLocation,
					'synonyms'      : json.dumps(list(self.synonyms)),
					'settings'      : json.dumps(self.settings)
				}
			)

			self.id = locationId


	def updateSettings(self, settings: dict):
		self.settings = {**self.settings, **settings}


	def updatesynonyms(self, synonyms):
		self.synonyms = synonyms


	@deprecated
	def getSaveName(self) -> str:
		return self.name.replace(' ', '_')


	def changeName(self, newName: str):
		self.name = newName
		self.DatabaseManager.update(
			tableName=self.LocationManager.LOCATIONS_TABLE,
			callerName=self.LocationManager.name,
			values={'name': newName},
			row=('id', self.id)
		)


	def addSynonym(self, synonym: str):
		self.synonyms.add(synonym)


	def deleteSynonym(self, synonym: str):
		try:
			self.synonyms.remove(synonym)
		except:
			raise Exception(synonym, constants.UNKNOWN)


	def toJson(self) -> str:
		return json.dumps({
			self.name: {
				'id'            : self.id,
				'name'          : self.name,
				'parentLocation': self.parentLocation,
				'synonyms'      : list(self.synonyms),
				'settings'      : self.settings
			}
		})


	def toDict(self) -> dict:
		return {
			'id'            : self.id,
			'name'          : self.name,
			'parentLocation': self.parentLocation,
			'synonyms'      : list(self.synonyms),
			'settings'      : self.settings
		}
