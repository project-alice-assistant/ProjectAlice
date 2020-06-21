from dataclasses import dataclass, field


@dataclass
class DialogTemplateSlotType:
	name: str
	automaticallyExtensible: bool
	useSynonyms: bool
	values: list = field(default_factory=list)
	matchingStrictness: float = 0
	myValues: dict = field(default_factory=dict)


	def __post_init__(self): #NOSONAR
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
