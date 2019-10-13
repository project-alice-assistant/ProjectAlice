from typing import Callable, Dict


class StateMachine:

	def __init__(self, defaultFunction: Callable, mapping: Dict[str, Callable]):
		self._defaultFunction = defaultFunction
		self._mapping = mapping
