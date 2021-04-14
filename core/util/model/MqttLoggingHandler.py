#  Copyright (c) 2021
#
#  This file, MqttLoggingHandler.py, is part of Project Alice.
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

from core.base.SuperManager import SuperManager
from core.commons import constants


class MqttLoggingHandler(logging.Handler):

	REGEX = re.compile(r'\[(?P<component>.*?)]\s*(?P<msg>.*)$')

	def __init__(self):
		super().__init__()
		self._history = list()


	def emit(self, record: logging.LogRecord) -> None:
		record.msg = self.format(record)
		matches = self.REGEX.search(record.msg)

		if matches:
			component = matches['component']
			msg = matches['msg']
		else:
			component = constants.UNKNOWN
			msg = record.msg

		payload = {
			'time': datetime.now().strftime('%H:%M:%S.%f')[:-3],
			'level': record.levelname,
			'msg' : msg,
			'component': component
		}

		self.saveToHistory(payload)

		if SuperManager.getInstance() and SuperManager.getInstance().mqttManager:
			SuperManager.getInstance().mqttManager.publish(
				topic=constants.TOPIC_SYSLOG,
				payload=payload
			)


	def saveToHistory(self, payload: dict):
		if len(self._history) >= 250:
			self._history.pop(0)

		self._history.append(payload)


	@property
	def history(self) -> list:
		return self._history
