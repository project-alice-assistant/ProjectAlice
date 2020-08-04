from core.asr.model.Asr import Asr


class SnipsAsr(Asr):

	NAME = 'Snips Asr'
	DEPENDENCIES = {
		'system': [
			'snips-asr-model-en-500mb'
		],
		'pip'   : {}
	}

	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = False


	def onStart(self):
		super().onStart()

		if self.LanguageManager.activeLanguage != 'en':
			raise Exception('Snips generic ASR only for english')

		if not self.ConfigManager.getSnipsConfiguration('snips-asr', 'model').contains('500'):
			self.ConfigManager.updateSnipsConfiguration('snips-asr', 'model', value='/usr/share/snips/snips-asr-model-en-500MB', restartSnips=True)

		result = self.Commons.runRootSystemCommand(['systemctl', 'start', 'snips-asr'])
		if result.returncode:
			self.logWarning('Snips ASR is not installed, installing...')
			installed = self.Commons.runRootSystemCommand(['apt', 'install', f'{self.Commons.rootDir()}/system/snips/snips-asr_0.64.0_armhf.deb'])
			if installed.returncode:
				raise Exception(f"Couldn't install Snips-ASR: {installed.stderr}")


	def onStop(self):
		super().onStop()
		self.Commons.runRootSystemCommand(['systemctl', 'stop', 'snips-asr'])
