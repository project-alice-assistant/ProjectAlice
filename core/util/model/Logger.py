import logging
import traceback

import re


class Logger:

	def __init__(self, prepend: str = None):
		self._prepend = prepend
		self._logger = logging.getLogger('ProjectAlice')


	def logInfo(self, msg: str):
		self.doLog(function='info', msg=msg, printStack=False)


	def logError(self, msg: str):
		self.doLog(function='error', msg=msg)
		self.printTraceback()


	def logDebug(self, msg: str):
		self.doLog(function='debug', msg=msg, printStack=False)


	def logFatal(self, msg: str):
		self.doLog(function='fatal', msg=msg)
		self.printTraceback()
		try:
			from core.base.SuperManager import SuperManager

			SuperManager.getInstance().projectAlice.onStop()
		except:
			exit()


	def logWarning(self, msg: str, printStack: bool = False):
		self.doLog(function='warning', msg=msg, printStack=printStack)
		self.printTraceback()


	def logCritical(self, msg: str):
		self.doLog(function='critical', msg=msg)
		self.printTraceback()


	def doLog(self, function: callable, msg: str, printStack = True):
		if self._prepend:
			msg = f'{self._prepend} {msg}'

		match = re.match(r'^(\[[\w ]+\])(.*)$', msg)
		if match:
			tag, log = match.groups()
			space = ''.join([' ' for _ in range(25 - len(tag))])
			msg = f'{tag}{space}{log}'

		func = getattr(self._logger, function)
		func(msg, exc_info=printStack)


	@staticmethod
	def printTraceback():
		from core.base.SuperManager import SuperManager

		try:
			if SuperManager.getInstance().configManager.getAliceConfigByName('debug'):
				traceback.print_exc()
		except:
			# Would mean that warning was triggered before configManager was even loaded
			pass
