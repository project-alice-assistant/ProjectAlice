import logging

from core.base.model.Manager import Manager


class LoggingManager(Manager):
	NAME = 'LoggingManager'

	def __init__(self):
		super().__init__(self.NAME)
		self._logger = logging.getLogger('ProjectAlice')


	def info(self, msg: str):
		self._logger.info(msg, exc_info=True)


	def error(self, msg: str):
		self._logger.error(msg, exc_info=True)


	def debug(self, msg: str):
		self._logger.debug(msg, exc_info=True)


	def fatal(self, msg: str):
		self._logger.fatal(msg, exc_info=True)


	def warning(self, msg: str):
		self._logger.warning(msg, exc_info=True)


	def critical(self, msg: str):
		self._logger.critical(msg, exc_info=True)
