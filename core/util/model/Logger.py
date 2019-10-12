import logging

class Logger:

	def __init__(self, *args, **kwargs):
		self._logger = logging.getLogger('ProjectAlice')


	def logInfo(self, msg: str):
		self._logger.info(msg, exc_info=True)


	def logError(self, msg: str):
		self._logger.error(msg, exc_info=True)


	def logDebug(self, msg: str):
		self._logger.debug(msg, exc_info=True)


	def logFatal(self, msg: str):
		self._logger.fatal(msg, exc_info=True)


	def logWarning(self, msg: str):
		self._logger.warning(msg, exc_info=True)


	def logCritical(self, msg: str):
		self._logger.critical(msg, exc_info=True)
