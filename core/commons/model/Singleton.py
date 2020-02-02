from core.util.model.Logger import Logger


class Singleton(Logger):

	INSTANCE = None

	def __init__(self, name):
		self.log = Logger(owner=name)

		if self.INSTANCE:
			self.log.error(f'Trying to instanciate {name} but instance already exists')
			raise KeyboardInterrupt
		else:
			self.INSTANCE = self


	@staticmethod
	def getInstance():
		return Singleton.INSTANCE
