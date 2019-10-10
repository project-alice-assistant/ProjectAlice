import getpass
import subprocess
import time
from pathlib import Path
from zipfile import ZipFile

import tempfile

from core.base.SuperManager import SuperManager
from core.base.model.Manager import Manager
from core.commons import commons, constants
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
			'snips-tts'
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


	def onSnipsAssistantInstalled(self):
		self.runCmd(cmd='restart')


	def onSnipsAssistantDownloaded(self, **kwargs):
		try:
			filepath = Path(tempfile.gettempdir(), 'assistant.zip')
			with ZipFile(filepath) as zipfile:
				zipfile.extractall(tempfile.gettempdir())

			subprocess.run(['sudo', 'rm', '-rf', commons.rootDir() + f'/trained/assistants/assistant_{self.LanguageManager.activeLanguage}'])
			subprocess.run(['sudo', 'rm', '-rf', commons.rootDir() + '/assistant'])
			subprocess.run(['sudo', 'cp', '-R', str(filepath).replace('.zip', ''), commons.rootDir() + f'/trained/assistants/assistant_{self.LanguageManager.activeLanguage}'])

			time.sleep(0.5)

			subprocess.run(['sudo', 'chown', '-R', getpass.getuser(), commons.rootDir() + f'/trained/assistants/assistant_{self.LanguageManager.activeLanguage}'])
			subprocess.run(['sudo', 'ln', '-sfn', commons.rootDir() + f'/trained/assistants/assistant_{self.LanguageManager.activeLanguage}', commons.rootDir() + '/assistant'])
			subprocess.run(['sudo', 'ln', '-sfn', commons.rootDir() + f'/system/sounds/{self.LanguageManager.activeLanguage}/start_of_input.wav', commons.rootDir() + '/assistant/custom_dialogue/sound/start_of_input.wav'])
			subprocess.run(['sudo', 'ln', '-sfn', commons.rootDir() + f'/system/sounds/{self.LanguageManager.activeLanguage}/end_of_input.wav', commons.rootDir() + '/assistant/custom_dialogue/sound/end_of_input.wav'])
			subprocess.run(['sudo', 'ln', '-sfn', commons.rootDir() + f'/system/sounds/{self.LanguageManager.activeLanguage}/error.wav', commons.rootDir() + '/assistant/custom_dialogue/sound/error.wav'])

			time.sleep(0.5)
			self.onSnipsAssistantInstalled()

			SuperManager.getInstance().broadcast(
				method='onSnipsAssistantInstalled',
				exceptions=[self.name],
				propagateToModules=True,
				**kwargs
			)
		except Exception as e:
			self._logger.error(f'[{self.name}] Failed installing Snips Assistant: {e}')
			SuperManager.getInstance().broadcast(
				method='onSnipsAssistantFailedInstalling',
				exceptions=[constants.DUMMY],
				propagateToModules=True,
				**kwargs
			)


	def runCmd(self, cmd: str, services: list = None):
		if not Path(commons.rootDir() + '/assistant').exists():
			self._logger.warning(f'[{self.name}] Assistant not yet existing, shouldn\'t handle Snips for now')
			return

		if not services:
			services = self._snipsServices

		for service in services:
			if (service == 'snips-asr' and not isinstance(self.ASRManager.asr, SnipsASR)) or (service == 'snips-tts' and not isinstance(self.TTSManager.tts, SnipsTTS)):
				continue

			result = subprocess.run(['sudo', 'systemctl', cmd, service], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			if result.returncode == 0:
				self._logger.info(f"[{self.name}] Service {service} {cmd}'ed")
			elif result.returncode == 5:
				pass
			else:
				self._logger.info(f"[{self.name}] Tried to {cmd} the {service} service but it returned with return code {result.returncode}")


	def toggleFeedbackSound(self, state: str, siteId: str = 'all'):
		topic = constants.TOPIC_HOTWORD_TOGGLE_ON if state == 'on' else constants.TOPIC_TOGGLE_FEEDBACK_OFF

		if siteId == 'all':
			devices = self.DeviceManager.getDevicesByType(deviceType='AliceSatellite', connectedOnly=True)
			for device in devices:
				self.MqttManager.publish(topic=topic, payload={'siteId': device.room})
		else:
			self.MqttManager.publish(topic=topic, payload={'siteId': siteId})
