from enum import IntEnum, unique


@unique
class AccessLevel(IntEnum):
	ADMIN = 1
	DEFAULT = 2
	KID = 3
	WORKER = 4
	GUEST = 5
