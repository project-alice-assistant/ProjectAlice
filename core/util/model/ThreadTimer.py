from dataclasses import dataclass, field
from threading import Timer

@dataclass
class ThreadTimer:
	callback: str
	args: list = field(default_factory=list)
	kwargs: dict = field(default_factory=dict)
	timer: Timer = None
