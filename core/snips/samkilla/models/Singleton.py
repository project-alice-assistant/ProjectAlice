class Singleton:
	INSTANCE = None


	def __init__(self, name: str):
		if self.INSTANCE:
			raise KeyboardInterrupt
		else:
			self.INSTANCE = self
			self._name = name
