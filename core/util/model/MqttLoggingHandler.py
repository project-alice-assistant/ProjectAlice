import logging

from core.base.SuperManager import SuperManager


class MqttLoggingHandler(logging.Handler):


	def __init__(self):
		super().__init__()


	def emit(self, record: logging.LogRecord) -> None:
		record.msg = self.format(record)

		if SuperManager.getInstance() and SuperManager.getInstance().mqttManager:
			SuperManager.getInstance().mqttManager.publish(
				topic='projectalice/logging/syslog',
				payload={
					'msg': record.msg
				}
			)
