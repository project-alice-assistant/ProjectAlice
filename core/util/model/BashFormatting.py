import logging

import re
from copy import copy
from enum import Enum


class BashStringFormatCode(Enum):
	SEQUENCE = '\\\\033[{}m'

	RESET = 0
	BOLD = 1
	DIM = 2
	UNDERLINED = 4

	DEFAULT = '39'
	RED = '31'
	GREEN = '32'
	YELLOW = '33'
	BLUE = '94'
	GREY = '90'


class Formatter(logging.Formatter):
	BOLD = re.compile(r'\*\*(.+?)\*\*')
	DIM = re.compile(r'--(.+?)--')
	UNDERLINED = re.compile(r'__(.+?)__')
	COLOR = re.compile(r'(?i)!\[(red|green|yellow|blue|gray)\]\((.+?)\)')

	GLUED_RESETS = re.compile(r'(?:\\033\[(?:0|2[1-8])m){2,}$')
	GLUED_CODES = re.compile(r'\\033\[([0-9]+?)m+')

	COLORS = {
		'WARNING' : BashStringFormatCode.YELLOW.value,
		'INFO'    : BashStringFormatCode.DEFAULT.value,
		'DEBUG'   : BashStringFormatCode.BLUE.value,
		'ERROR'   : BashStringFormatCode.RED.value,
		'CRITICAL': BashStringFormatCode.RED.value
	}


	def __init__(self):
		mask = '%(message)s'
		super().__init__(mask)


	# TODO implement mardown support for stdout
	def format(self, record: logging.LogRecord) -> str:
		level = record.levelname
		rec = copy(record)
		msg = rec.msg

		if level in self.COLORS:
			msg = f'\033[{self.COLORS[level]}m{record.msg}\033[0m'

		msg = self.BOLD.sub(r'\1', msg)
		msg = self.DIM.sub(r'\1', msg)
		msg = self.UNDERLINED.sub(r'\1', msg)
		msg = self.COLOR.sub(r'\2', msg)

		rec.msg = msg
		return logging.Formatter.format(self, rec)
