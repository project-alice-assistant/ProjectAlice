import logging
import inspect


class Logger:

	def __init__(self, depth: int = 4, *args, **kwargs):
		self._logger = logging.getLogger('ProjectAlice')
		self._depth = depth


	def logInfo(self, msg: str):
		self.doLog(function='info', msg=msg, printStack=False)


	def logError(self, msg: str):
		self.doLog(function='error', msg=msg)


	def logDebug(self, msg: str):
		self.doLog(function='debug', msg=msg, printStack=False)


	def logFatal(self, msg: str):
		self.doLog(function='fatal', msg=msg)


	def logWarning(self, msg: str, printStack: bool = False):
		self.doLog(function='warning', msg=msg, printStack=printStack)


	def logCritical(self, msg: str):
		self.doLog(function='critical', msg=msg)


	def doLog(self, function: callable, msg: str, printStack=True):
		func = getattr(self._logger, function)
		func(self.decorate(msg), exc_info=printStack)


	def decorate(self, msg: str) -> str:
		return f'[{inspect.getmodulename(inspect.stack()[self._depth][1])}] {msg}'
