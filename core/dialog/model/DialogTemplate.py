from dataclasses import dataclass, field
from typing import Generator

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


	@property
	def allIntents(self) -> Generator[DialogTemplateIntent, None, None]:
		for intent in self.myIntents.values():
			yield intent


	def fuseSlotType(self, otherSlot: DialogTemplateSlotType):
		mySlot: DialogTemplateSlotType = self.mySlotTypes.get(otherSlot.name, None)
		if not mySlot:
			return

		if not mySlot.useSynonyms and otherSlot.useSynonyms:
			mySlot.useSynonyms = True

		if not mySlot.automaticallyExtensible and otherSlot.automaticallyExtensible:
			mySlot.automaticallyExtensible = True

		myValues = {value['value']: value for value in mySlot.values}
		for otherValue in otherSlot.values:
			if otherValue['value'] not in myValues:
				# This slot value does not exist in original slot
				mySlot.values = mySlot.values.append(otherValue)
			else:
				newSynonyms = myValues[otherValue['value']]['synonyms']
				newSynonyms.extend(synonym for synonym in otherValue['synonyms'] if synonym not in newSynonyms)


	def dump(self) -> dict:
		return {
			'skill'      : f'{self.skill}',
			'icon'       : f'{self.icon}',
			'description': f'{self.description}',
			'slotTypes'  : [slot.dump() for slot in self.mySlotTypes.values()],
			'intents'    : [intent.dump() for intent in self.myIntents.values()]
		}
