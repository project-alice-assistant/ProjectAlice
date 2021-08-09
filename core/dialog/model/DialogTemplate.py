#  Copyright (c) 2021
#
#  This file, DialogTemplate.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:46 CEST

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator, List

from core.dialog.model.DialogTemplateIntent import DialogTemplateIntent
from core.dialog.model.DialogTemplateSlotType import DialogTemplateSlotType


@dataclass
class DialogTemplate:
	skill: str
	slotTypes: list
	intents: list

	mySlotTypes: dict = field(default_factory=dict)
	myIntents: dict = field(default_factory=dict)

	# TODO remove me
	icon: str = ''
	description: str = ''


	def __post_init__(self):  # NOSONAR
		for slotType in self.slotTypes:
			instance = DialogTemplateSlotType(**slotType)
			self.mySlotTypes[instance.name] = instance

		for intent in self.intents:
			instance = DialogTemplateIntent(**intent)
			self.myIntents[instance.name] = instance


	@property
	def allSlots(self) -> Generator[DialogTemplateSlotType, None, None]:
		for slot in self.mySlotTypes.values():
			yield slot


	def getSlot(self, slotName: str) -> DialogTemplateSlotType:
		return self.mySlotTypes.get(slotName, None)


	@property
	def allIntents(self) -> Generator[DialogTemplateIntent, None, None]:
		for intent in self.myIntents.values():
			yield intent


	def fuseSlotType(self, otherTemplate: DialogTemplate, slotName: str):
		mySlot: DialogTemplateSlotType = self.mySlotTypes.get(slotName, None)
		if not mySlot:
			return

		otherSlot = otherTemplate.getSlot(slotName)
		if not otherSlot:
			return

		if not mySlot.useSynonyms and otherSlot.useSynonyms:
			mySlot.useSynonyms = True

		if not mySlot.automaticallyExtensible and otherSlot.automaticallyExtensible:
			mySlot.automaticallyExtensible = True

		for otherValueName, otherValue in otherSlot.myValues.items():
			if otherValueName not in mySlot.myValues:
				# This slot value does not exist in original slot
				mySlot.addNewValue(otherValue)
			else:
				mySynonyms: List = mySlot.myValues.get('synonyms', {})
				otherSynonyms: List = otherValue.get('synonyms', list)

				for otherSynonym in otherSynonyms:
					if otherSynonym in mySynonyms:
						continue

					mySlot.addNewSynonym(otherValueName, otherSynonym)

		otherTemplate.removeSlotType(slotName)


	def removeSlotType(self, slotTypeName: str):
		self.mySlotTypes.pop(slotTypeName, None)


	def addUtterancesExtender(self, extender: Path):
		data = json.loads(extender.read_text())

		for intentName, intent in data.get('intents', dict()).items():
			for utterance in intent.get('utterances', list()):
				self.myIntents[intentName].addUtterance(utterance)


	def addUtterance(self, text: str, intentName: str):
		self.myIntents[intentName].addUtterance(text)


	def dump(self) -> dict:
		return {
			'skill'      : self.skill,
			'slotTypes'  : [slot.dump() for slot in self.mySlotTypes.values()],
			'intents'    : [intent.dump() for intent in self.myIntents.values()]
		}
