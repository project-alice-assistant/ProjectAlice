from core.base.SuperManager import SuperManager


class DialogState:

	def __init__(self, state: str):
		if ':' not in state:
			caller = SuperManager.getInstance().commons.getFunctionCaller(depth=2)
			state = f'{caller}:{state}'

		self._state = state


	def __eq__(self, other) -> bool:
		if ':' not in other:
			caller = SuperManager.getInstance().commons.getFunctionCaller()
			other = f'{caller}:{other}'

		return self._state == other


	def __ne__(self, other) -> bool:
		return not self.__eq__(other)


	def __repr__(self) -> str:
		return self._state


	def __str__(self) -> str:
		return self._state
