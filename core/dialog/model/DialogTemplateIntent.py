#  Copyright (c) 2021
#
#  This file, DialogTemplateIntent.py, is part of Project Alice.
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
class DialogTemplateIntent(object):
	name: str
	enabledByDefault: bool
	utterances: list = field(default_factory=list)
	slots: list = field(default_factory=list)

	# TODO remove me
	description: str = ''


	def addUtterance(self, text: str):
		self.utterances.append(text)


	def dump(self) -> dict:
		return {
			'name'            : self.name,
			'enabledByDefault': self.enabledByDefault,
			'utterances'      : self.utterances,
			'slots'           : self.slots
		}
