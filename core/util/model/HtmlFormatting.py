import logging

import re
from enum import Enum


class HtmlFormatting(Enum):
	SEQUENCE = '<span class="logLine {}">{}</span>'

	BOLD = 'logBold'
	DIM = 'logDim'
	UNDERLINED = 'logUnderlined'

	DEFAULT = 'logDefault'
	RED = 'logRed'
	GREEN = 'logGreen'
	YELLOW = 'logYellow'
	BLUE = 'logBlue'
	GREY = 'logGrey'


class Formatter(logging.Formatter):
	BOLD = re.compile(r'\*\*(.+?)\*\*')
	DIM = re.compile(r'--(.+?)--')
	UNDERLINED = re.compile(r'__(.+?)__')
	COLOR = re.compile(r'(?i)!\[(red|green|yellow|blue|gray)\]\((.+?)\)')

	GLUED_RESETS = re.compile(r'(?:\\033\[(?:0|2[1-8])m){2,}$')
	GLUED_CODES = re.compile(r'\\033\[([0-9]+?)m+')

	COLORS = {
		'WARNING' : HtmlFormatting.YELLOW.value,
		'INFO'    : HtmlFormatting.DEFAULT.value,
		'DEBUG'   : HtmlFormatting.BLUE.value,
		'ERROR'   : HtmlFormatting.RED.value,
		'CRITICAL': HtmlFormatting.RED.value
	}


	def __init__(self):
		mask = '%(message)s'
		super().__init__(mask)


	def format(self, record: logging.LogRecord) -> str:
		level = record.levelname
		msg = record.getMessage()

		if level in self.COLORS:
			msg = HtmlFormatting.SEQUENCE.value.format(self.COLORS[level], msg)

		return msg
