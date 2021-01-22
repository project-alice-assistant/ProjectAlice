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
