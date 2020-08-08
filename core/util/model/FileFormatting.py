import logging

import re
from copy import copy


class Formatter(logging.Formatter):
	BOLD = re.compile(r'\*\*(.+?)\*\*')
	DIM = re.compile(r'--(.+?)--')
	UNDERLINED = re.compile(r'__(.+?)__')
	COLOR = re.compile(r'(?i)!\[(red|green|yellow|blue|gray)]\((.+?)\)')


	def __init__(self):
		mask = '%(asctime)s [%(threadName)s] - [%(levelname)s] - %(message)s'
		super().__init__(mask)


	def format(self, record: logging.LogRecord) -> str:
		rec = copy(record)
		msg = rec.msg

		msg = self.BOLD.sub(r'\1', msg)
		msg = self.DIM.sub(r'\1', msg)
		msg = self.UNDERLINED.sub(r'\1', msg)
		msg = self.COLOR.sub(r'\2', msg)

		rec.msg = msg
		return logging.Formatter.format(self, rec)
