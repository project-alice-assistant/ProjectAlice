from enum import Enum


class ScenarioTileType(Enum):
	CONDITION_BLOCK = 10
	LOOP_BLOCK = 20
	VARIABLE = 30
	INTEGER = 40
	STRING = 50
	FLOAT = 60
	BOOLEAN = 70
	ARRAY = 80
	ACTION = 150
	EVENT = 200
