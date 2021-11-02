#  Copyright (c) 2021
#
#  This file, Furniture.py, is part of Project Alice.
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
		self.settings = {**self.settings, **settings}


	def toDict(self) -> dict:
		return {
			'id'            : self.id,
			'parentLocation': self.parentLocation,
			'settings'      : self.settings
		}
