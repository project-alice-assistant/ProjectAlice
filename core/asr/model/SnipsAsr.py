import time

from core.asr.model.Asr import Asr
from core.dialog.model.DialogSession import DialogSession


class SnipsAsr(Asr):

	NAME = 'Snips Asr'
	DEPENDENCIES = {
		'system': [
			'snips-asr',
			'snips-asr-model-en-500mb'
		],
		'pip'   : {}
	}

	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = False
		self._listening = False


	def onStartListening(self, session):
		self._listening = True


	def onAsrToggleOff(self, siteId: str):
		self._listening = False


	def decodeStream(self, session: DialogSession):
		while self._listening:
			time.sleep(0.1)


	def installDependencies(self) -> bool:
		self.logWarning('Snips ASR is not installed, installing...')
		installed = self.Commons.runRootSystemCommand(['apt', 'install', f'{self.Commons.rootDir()}/system/snips/snips-asr_0.64.0_armhf.deb'])
		self.logWarning('Downloading generic ASR, this may take a while')
		self.Commons.downloadFile(
			url='https://raspbian.snips.ai/stretch/pool/s/sn/snips-asr-model-en-500MB_0.6.0-alpha.4_armhf.deb',
			dest=f'{self.Commons.rootDir()}/system/snips/snips-asr-model-en-500MB_0.6.0-alpha.4_armhf.deb'
		)
		installed2 = self.Commons.runRootSystemCommand(['apt', 'install', f'{self.Commons.rootDir()}/system/snips/snips-asr-model-en-500MB_0.6.0-alpha.4_armhf.deb'])
		if installed.returncode or installed2.returncode:
			self.logError(f"Couldn't install Snips ASR: {installed.stderr}")
			return False

		return True


	def onStart(self):
		super().onStart()

		if self.LanguageManager.activeLanguage != 'en':
			raise Exception('Snips generic ASR only for english')

		if not '500' in str(self.ConfigManager.getSnipsConfiguration('snips-asr', 'model')):
			self.ConfigManager.updateSnipsConfiguration('snips-asr', 'model', value='/usr/share/snips/snips-asr-model-en-500MB', restartSnips=True)

		if not self.ConfigManager.getSnipsConfiguration('snips-asr', 'model', createIfNotExist=False):
			self.ConfigManager.updateSnipsConfiguration('snips-asr', 'partial', value='true', restartSnips=True)

		self.Commons.runRootSystemCommand(['systemctl', 'start', 'snips-asr'])


	def onStop(self):
		super().onStop()
		self.Commons.runRootSystemCommand(['systemctl', 'stop', 'snips-asr'])
