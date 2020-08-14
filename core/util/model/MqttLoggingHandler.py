import logging

from core.base.SuperManager import SuperManager
from core.commons import constants


class MqttLoggingHandler(logging.Handler):


	def __init__(self):
		super().__init__()
		self._history = list()


	def emit(self, record: logging.LogRecord) -> None:
		record.msg = self.format(record)
		self.saveToHistory(record.msg)

		if SuperManager.getInstance() and SuperManager.getInstance().mqttManager:
			SuperManager.getInstance().mqttManager.publish(
				topic=constants.TOPIC_SYSLOG,
				payload={
					'msg': record.msg
				}
			)


	def saveToHistory(self, msg: str):
		if len(self._history) >= 250:
			self._history.pop(0)
		self._history.append(msg)


	@property
	def history(self) -> list:
		return self._history
