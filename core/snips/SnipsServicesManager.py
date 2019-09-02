import subprocess

import core.base.Managers as managers
from core.base.Manager import Manager
from core.voice.model.SnipsASR import SnipsASR


class SnipsServicesManager(Manager):

	NAME = 'SnipsServicesManager'

	def __init__(self, mainClass):
		super().__init__(mainClass, self.NAME)
		managers.SnipsServicesManager = self

		self._snipsServices = [
			'snips-hotword',
			'snips-nlu',
			'snips-dialogue',
			'snips-injection',
			'snips-audio-server',
			'snips-asr'
		]


	def snipsServices(self, withASR: bool = True) -> list:
		if withASR:
			return self._snipsServices
		else:
			return [x for x in self._snipsServices if not 'asr' in x]


	def onStart(self):
		self.runCmd(cmd = 'start', services = self.snipsServices(withASR=False))


	def onStop(self):
		self.runCmd(cmd = 'stop', services = self.snipsServices())
		# return


	def runCmd(self, cmd: str, services: list = None):
		if not services:
			services = self._snipsServices

		for service in services:

			if service == 'snips-asr' and not isinstance(managers.ASRManager.asr, SnipsASR):
				continue

			result = subprocess.run(['sudo', 'systemctl', cmd, service], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			if result.returncode == 0:
				self._logger.info("[{}] Service {} {}'ed".format(self.name, service, cmd))
			else:
				self._logger.info("[{}] Tried to {} the {} service but it returned with return code {}".format(self.name, cmd, service, result.returncode))


	@staticmethod
	def toggleFeedbackSound(state: str, siteId: str = 'all'):
		topic = 'hermes/feedback/sound/toggleOn' if state == 'on' else 'hermes/feedback/sound/toggleOff'

		if siteId == 'all':
			devices = managers.DeviceManager.getDevicesByType(deviceType='AliceSatellite', connectedOnly=True)
			for device in devices:
				managers.MqttServer.publish(topic=topic, payload={'siteId': device.room})
		else:
			managers.MqttServer.publish(topic=topic, payload={'siteId': siteId})
