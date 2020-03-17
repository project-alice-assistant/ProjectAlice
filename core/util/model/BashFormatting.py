import logging

import re
from copy import copy
from enum import Enum


class BashStringFormatCode(Enum):
	# SEQUENCE = '\\\\033[{}m'
	SEQUENCE = '#033[{}m'

	RESET = 0
	BOLD = 1
	DIM = 2
	UNDERLINED = 4

	DEFAULT = '39'
	RED = '31'
	GREEN = '32'
	YELLOW = '33'
	BLUE = '94'
	GRAY = '90'


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


	def format(self, record: logging.LogRecord) -> str:
		level = record.levelname
		rec = copy(record)

		if level in self.COLORS:
			rec.msg = f'\033[{self.COLORS[level]}m{record.msg}\033[0m'

		return logging.Formatter.format(self, rec)

		# Replace markdown to bash code
		msg = self.BOLD.sub(r'{}\1{}'.format(
			BashStringFormatCode.SEQUENCE.value.format(BashStringFormatCode.BOLD.value),
			BashStringFormatCode.SEQUENCE.value.format(str(BashStringFormatCode.BOLD.value + 20))
		), msg)

		msg = self.DIM.sub(r'{}\1{}'.format(
			BashStringFormatCode.SEQUENCE.value.format(BashStringFormatCode.DIM.value),
			BashStringFormatCode.SEQUENCE.value.format(str(BashStringFormatCode.DIM.value + 20))
		), msg)

		msg = self.UNDERLINED.sub(r'{}\1{}'.format(
			BashStringFormatCode.SEQUENCE.value.format(BashStringFormatCode.UNDERLINED.value),
			BashStringFormatCode.SEQUENCE.value.format(str(BashStringFormatCode.UNDERLINED.value + 20))
		), msg)

		# Find reset codes that are together at the end and merge them
		msg = self.GLUED_RESETS.sub(BashStringFormatCode.SEQUENCE.value.format(BashStringFormatCode.RESET.value), msg)

		# Let's find starting codes that are together and merge them
		# matches = self.GLUED_CODES.finditer(msg)


		record.msg = msg
		return logging.Formatter.format(self, record)
