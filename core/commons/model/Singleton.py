import logging

class Singleton:

	INSTANCE 	= None

	def __init__(self, name):
		self._logger = logging.getLogger('ProjectAlice')

		if self.INSTANCE:
			self._logger.error(f'Trying to instanciate {name} but instance already exists')
			raise KeyboardInterrupt
		else:
			self.INSTANCE = self
