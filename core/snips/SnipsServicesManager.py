from pathlib import Path

from core.base.model.Manager import Manager
from core.commons import constants
from core.voice.model.SnipsTTS import SnipsTTS


class SnipsServicesManager(Manager):


	def __init__(self):
		super().__init__()

		self._snipsServices = [
			'snips-hotword',
			'snips-dialogue',
			'snips-audio-server',
			'snips-tts'
		]


	def snipsServices(self) -> list:
		return self._snipsServices


	def onStart(self):
		super().onStart()
		self.runCmd(cmd='start', services=self.snipsServices())


	def onStop(self):
		super().onStop()
		self.runCmd(cmd='stop', services=self.snipsServices())


	def runCmd(self, cmd: str, services: list = None):
		if not Path(self.Commons.rootDir() + '/assistant').exists():
			self.logWarning('Assistant not yet existing, shouldn\'t handle Snips for now')
			return

		if not services:
			services = self._snipsServices

		for service in services:
			if service == 'snips-tts' and not isinstance(self.TTSManager.tts, SnipsTTS):
				continue

			result = self.Commons.runRootSystemCommand(['systemctl', cmd, service])
			if result.returncode == 0:
				self.logInfo(f"Service {service} {cmd}'ed")
			elif result.returncode == 5:
				pass
			else:
				self.logInfo(f"Tried to {cmd} the {service} service but it returned with return code {result.returncode}")


	def toggleFeedbackSound(self, state: str, siteId: str = constants.ALL):
		topic = constants.TOPIC_TOGGLE_FEEDBACK_ON if state == 'on' else constants.TOPIC_TOGGLE_FEEDBACK_OFF

		if siteId == 'all':
			devices = self.DeviceManager.getDevicesByType(deviceType='AliceSatellite', connectedOnly=True)
			for device in devices:
				self.MqttManager.publish(topic=topic, payload={'siteId': device.room})

			self.MqttManager.publish(topic=topic, payload={'siteId': constants.DEFAULT_SITE_ID})
		else:
			self.MqttManager.publish(topic=topic, payload={'siteId': siteId})
