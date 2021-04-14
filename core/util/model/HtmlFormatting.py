#  Copyright (c) 2021
#
#  This file, HtmlFormatting.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:48 CEST

import logging
import re
from datetime import datetime
from enum import Enum
from typing import Match


class HtmlFormatting(Enum):
	LOG = '<span class="logLine {}">{}</span>'
	INLINE = '<span class="log {}">{}</span>'

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
	COLOR = re.compile(r'(?i)!\[(red|green|yellow|blue|grey)]\((.+?)\)')
	THE_REST = re.compile(r'</span>(.+?)<span')

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
		now = datetime.now().strftime('%H:%M:%S.%f')[:-3]
		msg = f'<span class="log">[--{now}--] {msg}</span>'
		msg = self.BOLD.sub(HtmlFormatting.INLINE.value.format(HtmlFormatting.BOLD.value, r'\1'), msg)
		msg = self.UNDERLINED.sub(HtmlFormatting.INLINE.value.format(HtmlFormatting.UNDERLINED.value, r'\1'), msg)
		msg = self.DIM.sub(HtmlFormatting.INLINE.value.format(HtmlFormatting.DIM.value, r'\1'), msg)
		msg = self.COLOR.sub(self.colorFormat, msg)

		if level in self.COLORS:
			msg = HtmlFormatting.LOG.value.format(self.COLORS[level], msg)

		return msg


	@staticmethod
	def colorFormat(matching: Match) -> str:
		color = matching.group(1).title()
		return HtmlFormatting.INLINE.value.format(f'log{color}', matching.group(2))
