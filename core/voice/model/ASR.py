class ASR:
	def __init__(self):
		self._capableOfArbitraryCapture = False

	@property
	def capableOfArbitraryCapture(self) -> bool:
		return self._capableOfArbitraryCapture
