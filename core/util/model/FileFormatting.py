#  Copyright (c) 2021
#
#  This file, FileFormatting.py, is part of Project Alice.
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
