from core.util.model.Logger import Logger


class Singleton(Logger):

	INSTANCE = None

	def __init__(self, name):
		super().__init__()

		if self.INSTANCE:
			self.logError(f'Trying to instanciate {name} but instance already exists')
			raise KeyboardInterrupt
		else:
			self.INSTANCE = self


	@staticmethod
	def getInstance():
		return Singleton.INSTANCE
