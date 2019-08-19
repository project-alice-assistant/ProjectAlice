# -*- coding: utf-8 -*-


import logging

class Singleton:

	INSTANCE 	= None

	def __init__(self, name):
		self._logger = logging.getLogger('ProjectAlice')

		if self.INSTANCE:
			self._logger.error('Trying to instanciate {} but instance already exists'.format(name))
			raise KeyboardInterrupt
		else:
			self.INSTANCE = self
