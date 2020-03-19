import logging
from typing import Match

import re
from copy import copy
from enum import Enum


class BashStringFormatCode(Enum):
	SEQUENCE = '\033[{}m{}\033[{}m'

	RESET = 0
	BOLD = 1
	DIM = 2
	UNDERLINED = 4

	DEFAULT = 39
	RED = 31
	GREEN = 32
	YELLOW = 33
	BLUE = 94
	GREY = 90


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


	# TODO implement markdown support for stdout
	def format(self, record: logging.LogRecord) -> str:
		level = record.levelname
		rec = copy(record)
		msg = rec.msg

		if level in self.COLORS:
			msg = BashStringFormatCode.SEQUENCE.value.format(self.COLORS[level], msg, BashStringFormatCode.RESET.value)

		msg = self.BOLD.sub(BashStringFormatCode.SEQUENCE.value.format(BashStringFormatCode.BOLD.value, r'\1', 2), msg)
		msg = self.DIM.sub(BashStringFormatCode.SEQUENCE.value.format(BashStringFormatCode.DIM.value, r'\1', BashStringFormatCode.DIM.value + 20), msg)
		msg = self.UNDERLINED.sub(BashStringFormatCode.SEQUENCE.value.format(BashStringFormatCode.UNDERLINED.value, r'\1', BashStringFormatCode.UNDERLINED.value + 20), msg)
		# msg = self.COLOR.sub(self.colorFormat, msg)

		return msg


	@staticmethod
	def colorFormat(m: Match) -> str:
		color = m.group(1).title()

		if color == 'red':
			code = BashStringFormatCode.RED.value
		elif color == 'green':
			code = BashStringFormatCode.GREEN.value
		elif color == 'yellow':
			code = BashStringFormatCode.YELLOW.value
		elif color == 'blue':
			code = BashStringFormatCode.BLUE.value
		elif color == 'grey':
			code = BashStringFormatCode.GREY.value
		else:
			code = BashStringFormatCode.DEFAULT.value

		return BashStringFormatCode.SEQUENCE.value.format(code, m.group(2), BashStringFormatCode.DEFAULT)
