import logging
from queue import Queue

from core.base.SuperManager import SuperManager


class MqttLoggingHandler(logging.Handler):

	def __init__(self):
		super().__init__()
		self._buffer = Queue()


	def emit(self, record: logging.LogRecord) -> None:
		record.msg = self.format(record)

		if not SuperManager.getInstance() or not SuperManager.getInstance().mqttManager:
			# cache the logs until mqtt manager is started
			self._buffer.put(record.msg)
			return

		if not self._buffer.empty():
			while not self._buffer.empty():
				SuperManager.getInstance().mqttManager.publish(
					topic='projectalice/logging/syslog',
					payload={
						'msg': self._buffer.get()
					}
				)

		SuperManager.getInstance().mqttManager.publish(
			topic='projectalice/logging/syslog',
			payload={
				'msg': record.msg
			}
		)
