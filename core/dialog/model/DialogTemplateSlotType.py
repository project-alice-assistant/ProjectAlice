#  Copyright (c) 2021
#
#  This file, DialogTemplateSlotType.py, is part of Project Alice.
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

from dataclasses import dataclass, field


@dataclass
class DialogTemplateSlotType:
	name: str
	automaticallyExtensible: bool
	useSynonyms: bool
	values: list = field(default_factory=list)
	matchingStrictness: float = 0
	myValues: dict = field(default_factory=dict)
	technicalValue: bool = False


	def __post_init__(self):  # NOSONAR
		for value in self.values:
			self.myValues[value['value']] = value


	def addNewValue(self, value: dict):
		self.myValues[value['value']] = value


	def addNewSynonym(self, valueName: str, synonym: str):
		value = self.myValues.get(valueName, None)
		if not value:
			return

		self.myValues[valueName] = value.get('synonyms', list).append(synonym)


	def dump(self) -> dict:
		return {
			'name'                   : self.name,
			'matchingStrictness'     : self.matchingStrictness,
			'automaticallyExtensible': self.automaticallyExtensible,
			'useSynonyms'            : self.useSynonyms,
			'values'                 : list(self.myValues.values())
		}
