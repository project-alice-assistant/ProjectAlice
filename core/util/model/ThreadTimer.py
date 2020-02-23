from dataclasses import dataclass, field
from threading import Timer
from typing import Callable


@dataclass
class ThreadTimer:
	callback: Callable
	args: list = field(default_factory=list)
	kwargs: dict = field(default_factory=dict)
	timer: Timer = None
