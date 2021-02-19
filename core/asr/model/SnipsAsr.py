import threading
import time

import subprocess

from core.asr.model.Asr import Asr
from core.dialog.model.DialogSession import DialogSession


class SnipsAsr(Asr):

	NAME = 'Snips Asr'
	DEPENDENCIES = {
		'internal': {
			'snips-kaldi-atlas': 'system/snips/snips-kaldi-atlas_0.26.1_armhf.deb',
			'snips-asr': 'system/snips/snips-asr_0.64.0_armhf.deb'
		},
		'external': {
			'snips-asr-model-en-500mb': 'https://raspbian.snips.ai/stretch/pool/s/sn/snips-asr-model-en-500MB_0.6.0-alpha.4_armhf.deb'
		},
		'system': [
			'libgfortran3'
		],
		'pip'     : []
	}


	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = False
		self._listening = False
		self._thread: threading.Thread = self.ThreadManager.newThread(name='asrEngine', target=self.run, autostart=False)
		self._flag = threading.Event()


	def installDependencies(self):
		super().installDependencies()
		self.Commons.runRootSystemCommand(['systemctl', 'stop', 'snips-asr'])
		self.Commons.runRootSystemCommand(['systemctl', 'disable', 'snips-asr'])


	def onStartListening(self, session):
		self._listening = True


	def onAsrToggleOff(self, deviceUid: str):
		self._listening = False


	def decodeStream(self, session: DialogSession):
		while self._listening:
			time.sleep(0.1)


	def onStart(self):
		super().onStart()

		if self.LanguageManager.activeLanguage != 'en':
			raise Exception('Snips generic ASR only for english')

		self._flag.clear()
		if self._thread.is_alive():
			self._thread.join(timeout=5)

		self._thread.start()


	def run(self):
		cmd = f'snips-asr --assistant {self.Commons.rootDir()}/assistant --mqtt {self.ConfigManager.getAliceConfigByName("mqttHost")}:{self.ConfigManager.getAliceConfigByName("mqttPort")}'

		if self.ConfigManager.getAliceConfigByName('mqttUser'):
			cmd += f' --mqtt-username {self.ConfigManager.getAliceConfigByName("mqttUser")} --mqtt-password {self.ConfigManager.getAliceConfigByName("mqttPassword")}'

		if self.ConfigManager.getAliceConfigByName('mqttTLSFile'):
			cmd += f' --mqtt-tls-cafile {self.ConfigManager.getAliceConfigByName("mqttTLSFile")}'

		cmd += f' --model /usr/share/snips/snips-asr-model-en-500MB'
		cmd += f' --partial'

		process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

		self._flag.set()
		try:
			while self._flag.is_set():
				time.sleep(0.5)
		finally:
			process.terminate()


	def onStop(self):
		super().onStop()
		self._flag.clear()
		if self._thread.is_alive():
			self.ThreadManager.terminateThread(name='asrEngine')
