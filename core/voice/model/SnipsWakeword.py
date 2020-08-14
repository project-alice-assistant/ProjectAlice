from core.voice.model.WakewordEngine import WakewordEngine


class SnipsWakeword(WakewordEngine):

	NAME = 'Snips hotword'
	DEPENDENCIES = {
		'system': [
			'snips-hotword',
			'snips-hotword-model-heysnipsv4'
		],
		'pip': []
	}


	def installDependencies(self) -> bool:
		installed = self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', f'{self.Commons.rootDir()}/system/snips/snips-hotword_0.64.0_armhf.deb'])
		installed2 = self.Commons.runRootSystemCommand(['apt-get', 'install', '-y', f'{self.Commons.rootDir()}/system/snips/snips-hotword-model-heysnipsv4_0.64.0_armhf.deb'])
		if installed.returncode or installed2.returncode:
			self.logError(f"Couldn't install Snips wakeword: {installed.stderr}")
			return False


	def onStop(self):
		super().onStop()
		self.Commons.runRootSystemCommand(['systemctl', 'stop', 'snips-hotword'])


	def onStart(self):
		super().onStart()
		self.Commons.runRootSystemCommand(['systemctl', 'start', 'snips-hotword'])
