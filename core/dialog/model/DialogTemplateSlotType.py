from dataclasses import dataclass, field


@dataclass
class DialogTemplateSlotType:

	name: str
	automaticallyExtensible: bool
	useSynonyms: bool
	values: list = field(default_factory=list)
	matchingStrictness: float = 0
