import logging


class Logger:

	def __init__(self, owner: str = None):
		self._owner = owner
		self._logger = logging.getLogger('ProjectAlice')


	def info(self, msg: str):
		self.doLog(function='info', msg=msg, printStack=False)


	def error(self, msg: str):
		self.doLog(function='error', msg=msg)


	def debug(self, msg: str):
		self.doLog(function='debug', msg=msg, printStack=False)


	def fatal(self, msg: str):
		self.doLog(function='fatal', msg=msg)


	def warning(self, msg: str, printStack: bool = False):
		self.doLog(function='warning', msg=msg, printStack=printStack)


	def critical(self, msg: str):
		self.doLog(function='critical', msg=msg)


	def doLog(self, function: callable, msg: str, printStack=True):
		func = getattr(self._logger, function)
		func(f'[{self._owner or "Unknown"}] {msg}', exc_info=printStack)
