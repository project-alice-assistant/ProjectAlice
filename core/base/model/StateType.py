from enum import Enum


class StateType(Enum):
	BORN = 0
	RUNNING = 1
	DEAD = 2
	WAITING = 3
	FINISHED = 4
	STOPPED = 5
	CRASHED = 6
	KILLED = 7
	BOOTING = 8
	ERROR = 9
