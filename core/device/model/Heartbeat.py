from time import time

import paho.mqtt.client as mqtt

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants


class Heartbeat(ProjectAliceObject):

	def __init__(self, tempo: int = 2, topic: str = constants.TOPIC_CORE_HEARTBEAT):
		super().__init__()
		self._client = None
		self._tempo = tempo
		self._topic = topic
		self._rnd = 0
		self.startHeartbeat()


	def startHeartbeat(self):
		self._rnd = int(time())
		self.ThreadManager.newThread(name=f'heartBeatThread-{self._rnd}', target=self.thread)


	def stopHeartBeat(self):
		self.ThreadManager.terminateThread(name=f'heartBeatThread-{self._rnd}')


	def thread(self):
		self._client = mqtt.Client()

		if self.ConfigManager.getAliceConfigByName('mqttUser') and self.ConfigManager.getAliceConfigByName('mqttPassword'):
			self._client.username_pw_set(self.ConfigManager.getAliceConfigByName('mqttUser'), self.ConfigManager.getAliceConfigByName('mqttPassword'))

		if self.ConfigManager.getAliceConfigByName('mqttTLSFile'):
			self._client.tls_set(certfile=self.ConfigManager.getAliceConfigByName('mqttTLSFile'))
			self._client.tls_insecure_set(False)

		self._client.connect(self.ConfigManager.getAliceConfigByName('mqttHost'), int(self.ConfigManager.getAliceConfigByName('mqttPort')))
		self._client.loop_start()
		self.beat()


	def beat(self):
		if not self.ProjectAlice.shuttingDown:
			self._client.publish(topic=self._topic, payload=None, qos=0, retain=False)
		self.ThreadManager.newTimer(interval=self._tempo, func=self.beat)
