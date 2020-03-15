import logging

import re
from enum import Enum


class BashStringFormatCode(Enum):
	PREFIX = '\\\\033['
	SUFFIX = 'm'

	BOLD = '1'
	DIM = '2'
	UNDERLINED = '4'
	RESET = '\\\\033[0m'

	DEFAULT = '39'
	RED = '31'
	GREEN = '32'
	YELLOW = '33'
	BLUE = '34'
	GRAY = '90'


class Formatter(logging.Formatter):
	BOLD = re.compile(r'\*\*(.+?)\*\*')
	DIM = re.compile(r'--(.+?)--')
	UNDERLINED = re.compile(r'__(.+?)__')
	COLOR = re.compile(r'(?i)!\[(red|green|yellow|blue|gray)\]\((.+?)\)')

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
		if level in self.COLORS:
			record.msg = f'\033[{self.COLORS[level]}m{record.msg}'
		return logging.Formatter.format(self, record)


	@classmethod
	def formatString(cls, string: str) -> str:
		string = cls.BOLD.sub(r'{}{}{}\1{}'.format(
			BashStringFormatCode.PREFIX.value,
			BashStringFormatCode.BOLD.value,
			BashStringFormatCode.SUFFIX.value,
			BashStringFormatCode.RESET.value
		), string)
		print(string)

		return string
