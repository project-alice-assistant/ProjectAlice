from dataclasses import dataclass, field
from typing import Dict, Union, Optional

@dataclass
class Slot:
	slotName: str
	entity: str
	rawValue: str
	value: Dict[str, Union[str, int]]
	range: Dict[str, int]
	alternatives: list = field(default_factory=list)
	confidenceScore: Optional[float] = None
