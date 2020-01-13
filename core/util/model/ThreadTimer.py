import attr
from threading import Timer

@attr.s(slots=True, auto_attribs=True)
class ThreadTimer:
	callback: str
	args: list = attr.ib(default=attr.Factory(list))
	kwargs: dict = attr.ib(default=attr.Factory(dict))
	timer: Timer = None
