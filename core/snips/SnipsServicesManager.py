import getpass
import time
from pathlib import Path
from zipfile import ZipFile

import tempfile

from core.asr.model.SnipsASR import SnipsASR
from core.base.model.Manager import Manager
from core.commons import constants
from core.voice.model.SnipsTTS import SnipsTTS


class SnipsServicesManager(Manager):


	def __init__(self):
		super().__init__()

		self._snipsServices = [
			'snips-hotword',
			'snips-nlu',
			'snips-dialogue',
			'snips-injection',
			'snips-audio-server',
			'snips-asr',
			'snips-tts'
		]


	def snipsServices(self, withASR: bool = True) -> list:
		if withASR:
			return self._snipsServices
		else:
			return [x for x in self._snipsServices if 'asr' not in x]


	def onStart(self):
		self.runCmd(cmd='start', services=self.snipsServices(withASR=False))


	def onStop(self):
		self.runCmd(cmd='stop', services=self.snipsServices())


	def onSnipsAssistantInstalled(self, **kwargs):
		self.runCmd(cmd='restart')
		time.sleep(1)


	def onSnipsAssistantDownloaded(self, **kwargs):
		try:
			filepath = Path(tempfile.gettempdir(), 'assistant.zip')
			with ZipFile(filepath) as zipfile:
				zipfile.extractall(tempfile.gettempdir())

			self.Commons.runRootSystemCommand(['rm', '-rf', self.Commons.rootDir() + f'/trained/assistants/assistant_{self.LanguageManager.activeLanguage}'])
			self.Commons.runRootSystemCommand(['rm', '-rf', self.Commons.rootDir() + '/assistant'])
			self.Commons.runRootSystemCommand(['cp', '-R', str(filepath).replace('.zip', ''), self.Commons.rootDir() + f'/trained/assistants/assistant_{self.LanguageManager.activeLanguage}'])

			time.sleep(0.5)

			self.Commons.runRootSystemCommand(['chown', '-R', getpass.getuser(), self.Commons.rootDir() + f'/trained/assistants/assistant_{self.LanguageManager.activeLanguage}'])
			self.Commons.runRootSystemCommand(['ln', '-sfn', self.Commons.rootDir() + f'/trained/assistants/assistant_{self.LanguageManager.activeLanguage}', self.Commons.rootDir() + '/assistant'])
			self.Commons.runRootSystemCommand(['ln', '-sfn', self.Commons.rootDir() + f'/system/sounds/{self.LanguageManager.activeLanguage}/start_of_input.wav', self.Commons.rootDir() + '/assistant/custom_dialogue/sound/start_of_input.wav'])
			self.Commons.runRootSystemCommand(['ln', '-sfn', self.Commons.rootDir() + f'/system/sounds/{self.LanguageManager.activeLanguage}/end_of_input.wav', self.Commons.rootDir() + '/assistant/custom_dialogue/sound/end_of_input.wav'])
			self.Commons.runRootSystemCommand(['ln', '-sfn', self.Commons.rootDir() + f'/system/sounds/{self.LanguageManager.activeLanguage}/error.wav', self.Commons.rootDir() + '/assistant/custom_dialogue/sound/error.wav'])

			time.sleep(0.5)
			self.onSnipsAssistantInstalled()

			self.broadcast(
				method='onSnipsAssistantInstalled',
				exceptions=[self.name],
				propagateToSkills=True,
				**kwargs
			)
		except Exception as e:
			self.logError(f'Failed installing Snips Assistant: {e}')
			self.broadcast(
				method='onSnipsAssistantFailedInstalling',
				exceptions=[constants.DUMMY],
				propagateToSkills=True,
				**kwargs
			)


	def runCmd(self, cmd: str, services: list = None):
		if not Path(self.Commons.rootDir() + '/assistant').exists():
			self.logWarning('Assistant not yet existing, shouldn\'t handle Snips for now')
			return

		if not services:
			services = self._snipsServices

		for service in services:
			if (service == 'snips-asr' and not isinstance(self.ASRManager.asr, SnipsASR)) or (service == 'snips-tts' and not isinstance(self.TTSManager.tts, SnipsTTS)):
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
