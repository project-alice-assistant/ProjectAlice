import attr
from typing import Dict, Union

@attr.s(slots=True, frozen=True, auto_attribs=True)
class Slot:
	slotName: str
	entity: str
	rawValue: str
	value: Dict[str, Union[str, int]]
	range: Dict[str, int]
