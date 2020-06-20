import json
from dataclasses import dataclass, field


@dataclass
class DialogTemplateSlotType:
	name: str
	automaticallyExtensible: bool
	useSynonyms: bool
	values: list = field(default_factory=list)
	matchingStrictness: float = 0


	def toJson(self) -> str:
		return json.dumps({
			'name'                   : f'{self.name}',
			'matchingStrictness'     : f'{self.matchingStrictness}',
			'automaticallyExtensible': f'{self.automaticallyExtensible}',
			'useSynonyms'            : f'{self.useSynonyms}',
			'values'                 : f'{self.values}'
		}, ensure_ascii=False, indent=4)
