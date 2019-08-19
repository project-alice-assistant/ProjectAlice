
class Singleton:

	INSTANCE 	= None

	def __init__(self, name):
		if self.INSTANCE:
			raise KeyboardInterrupt
		else:
			self.INSTANCE = self
