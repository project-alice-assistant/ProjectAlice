from pathlib import Path
from typing import Union

from core.base.model.Manager import Manager
from core.commons import constants
from core.voice.model.SnipsTTS import SnipsTTS


class SnipsServicesManager(Manager):


	def __init__(self):
		super().__init__()

		self._snipsServices = [
			'snips-hotword',
			'snips-tts'
		]


	def snipsServices(self) -> list:
		return self._snipsServices


	def onStart(self):
		super().onStart()
		self.runCmd(cmd='start')


	def onStop(self):
		super().onStop()
		self.runCmd(cmd='stop')


	def runCmd(self, cmd: str, services: Union[str, list] = None):
		if not Path(self.Commons.rootDir() + '/assistant').exists():
			self.logWarning('Assistant not yet existing, shouldn\'t handle Snips for now')
			return

		if not services:
			services = self._snipsServices.copy()
			if self.ConfigManager.getAliceConfigByName('disableSoundAndMic') and 'snips-hotword' in services:
				services.remove('snips-hotword')

		if isinstance(services, str):
			services = [services]

		for service in services:
			if service == 'snips-tts' and not isinstance(self.TTSManager.tts, SnipsTTS):
				continue

			result = self.Commons.runRootSystemCommand(['systemctl', cmd, service])
			if result.returncode == 0:
				self.logInfo(f"{cmd.title()} service {service} ok")
			elif result.returncode != 5:
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
