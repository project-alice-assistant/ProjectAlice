import logging
import traceback
from typing import Match

import re


class Logger:

	def __init__(self, prepend: str = None):
		self._prepend = prepend
		self._logger = logging.getLogger('ProjectAlice')


	def logInfo(self, msg: str, plural: str = None):
		self.doLog(function='info', msg=msg, printStack=False, plural=plural)


	def logError(self, msg: str, plural: str = None):
		self.doLog(function='error', msg=msg, plural=plural)
		self.printTraceback()


	def logDebug(self, msg: str, plural: str = None):
		self.doLog(function='debug', msg=msg, printStack=False, plural=plural)


	def logFatal(self, msg: str, plural: str = None):
		self.doLog(function='fatal', msg=msg, plural=plural)
		self.printTraceback()
		try:
			from core.base.SuperManager import SuperManager

			SuperManager.getInstance().projectAlice.onStop()
		except:
			exit()


	def logWarning(self, msg: str, printStack: bool = False, plural: str = None):
		self.doLog(function='warning', msg=msg, printStack=printStack, plural=plural)
		self.printTraceback()


	def logCritical(self, msg: str, plural: str = None):
		self.doLog(function='critical', msg=msg, plural=plural)
		self.printTraceback()


	def doLog(self, function: callable, msg: str, printStack = True, plural: str = None):
		if plural:
			msg = self.doPlural(string=msg, word=plural)

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
	def doPlural(string: str, word: str) -> str:
		def plural(match: Match) -> str:
			matched = match.group()
			if int(match.group(1)) > 1:
				return matched + 's'
			return matched

		return re.sub(r'([\d]+)(.*?)({})'.format(word), plural, string)


	@staticmethod
	def printTraceback():
		from core.base.SuperManager import SuperManager
		if SuperManager.getInstance().configManager.getAliceConfigByName('debug'):
			traceback.print_exc()
