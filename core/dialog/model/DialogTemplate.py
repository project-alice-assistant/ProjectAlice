from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generator, List

from core.dialog.model.DialogTemplateIntent import DialogTemplateIntent
from core.dialog.model.DialogTemplateSlotType import DialogTemplateSlotType


@dataclass
class DialogTemplate:
	skill: str
	icon: str
	description: str
	slotTypes: list
	intents: list

	mySlotTypes: dict = field(default_factory=dict)
	myIntents: dict = field(default_factory=dict)


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
				mySynonyms: List = mySlot.myValues.get('synonyms', list)
				otherSynonyms: List = otherValue.get('synonyms', list)

				for otherSynonym in otherSynonyms:
					if otherSynonym in mySynonyms:
						continue

					mySlot.addNewSynonym(otherValueName, otherSynonym)

		otherTemplate.removeSlotType(slotName)


	def removeSlotType(self, slotTypeName: str):
		self.mySlotTypes.pop(slotTypeName, None)


	def addUtterance(self, text: str, intentName: str):
		self.myIntents[intentName].addUtterance(text)


	def dump(self) -> dict:
		return {
			'skill'      : self.skill,
			'icon'       : self.icon,
			'description': self.description,
			'slotTypes'  : [slot.dump() for slot in self.mySlotTypes.values()],
			'intents'    : [intent.dump() for intent in self.myIntents.values()]
		}
