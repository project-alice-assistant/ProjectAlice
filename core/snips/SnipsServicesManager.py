import subprocess
from pathlib import Path

from core.base.model.Manager import Manager
from core.commons import commons
from core.voice.model.SnipsASR import SnipsASR
from core.voice.model.SnipsTTS import SnipsTTS


class SnipsServicesManager(Manager):

	NAME = 'SnipsServicesManager'

	def __init__(self):
		super().__init__(self.NAME)

		self._snipsServices = [
			'snips-hotword',
			'snips-nlu',
			'snips-dialogue',
			'snips-injection',
			'snips-audio-server',
			'snips-asr',
			'snips-tts',
			'snips-makers-tts'
		]


	def snipsServices(self, withASR: bool = True) -> list:
		if withASR:
			return self._snipsServices
		else:
			return [x for x in self._snipsServices if not 'asr' in x]


	def onStart(self):
		self.runCmd(cmd='start', services=self.snipsServices(withASR=False))


	def onStop(self):
		self.runCmd(cmd='stop', services=self.snipsServices())


	def runCmd(self, cmd: str, services: list = None):
		if not Path(commons.rootDir() + '/assistant').exists():
			self._logger.warning('[{}] Assistant not yet existing, shouldn\'t handle Snips for now'.format(self.name))
			return

		if not services:
			services = self._snipsServices

		for service in services:
			if (service == 'snips-asr' and not isinstance(self.ASRManager.asr, SnipsASR)) or (service == 'snips-tts' and not isinstance(self.TTSManager.tts, SnipsTTS)):
				continue

			result = subprocess.run(['sudo', 'systemctl', cmd, service], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			if result.returncode == 0:
				self._logger.info("[{}] Service {} {}'ed".format(self.name, service, cmd))
			else:
				self._logger.info("[{}] Tried to {} the {} service but it returned with return code {}".format(self.name, cmd, service, result.returncode))


	def toggleFeedbackSound(self, state: str, siteId: str = 'all'):
		topic = 'hermes/feedback/sound/toggleOn' if state == 'on' else 'hermes/feedback/sound/toggleOff'

		if siteId == 'all':
			devices = self.DeviceManager.getDevicesByType(deviceType='AliceSatellite', connectedOnly=True)
			for device in devices:
				self.MqttManager.publish(topic=topic, payload={'siteId': device.room})
		else:
			self.MqttManager.publish(topic=topic, payload={'siteId': siteId})
