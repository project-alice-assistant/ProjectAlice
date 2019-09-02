from enum import Enum, unique


@unique
class AccessLevel(Enum):
	ADMIN =  1
	DEFAULT = 2
	KID = 3
	WORKER = 4
	GUEST = 5
