#  Copyright (c) 2021
#
#  This file, BashFormatting.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:47 CEST

import logging
import re
from copy import copy
from enum import Enum
from typing import Match


class BashStringFormatCode(Enum):
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
	COLOR = re.compile(r'(?i)!\[(red|green|yellow|blue|gray)]\((.+?)\)')

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
		self._baseColor = BashStringFormatCode.DEFAULT.value


	def format(self, record: logging.LogRecord) -> str:
		level = record.levelname
		rec = copy(record)
		msg = rec.msg

		if level in self.COLORS:
			msg = f'\033[{self.COLORS[level]}m{msg}\033[0m'
			self._baseColor = self.COLORS[level]

		msg = self.BOLD.sub(f'\033[{BashStringFormatCode.BOLD.value}m' + r'\1' + f'\033[{BashStringFormatCode.RESET.value};{self._baseColor}m', msg)
		msg = self.DIM.sub(f'\033[{BashStringFormatCode.DIM.value}m' + r'\1' + f'\033[{BashStringFormatCode.RESET.value};{self._baseColor}m', msg)
		msg = self.UNDERLINED.sub(f'\033[{BashStringFormatCode.UNDERLINED.value}m' + r'\1' + f'\033[{BashStringFormatCode.RESET.value};{self._baseColor}m', msg)
		msg = self.COLOR.sub(self.colorFormat, msg)

		return msg


	def colorFormat(self, matching: Match) -> str:
		color = getattr(BashStringFormatCode, matching.group(1).upper()).value
		return f'\033[{color}m{matching.group(2)}\033[{BashStringFormatCode.RESET.value};{self._baseColor}m'
