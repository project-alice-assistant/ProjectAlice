from dataclasses import dataclass

@dataclass
class Slot:
	slotName: str
	entity: str
	rawValue: str
	value: str
	range: str
