
class Singleton:

	INSTANCE = None

	def __init__(self):
		if self.INSTANCE:
			raise KeyboardInterrupt
		else:
			self.INSTANCE = self
