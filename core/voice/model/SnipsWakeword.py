from core.voice.model.WakewordEngine import WakewordEngine


class SnipsWakeword(WakewordEngine):

	NAME = 'Snips hotword'
	DEPENDENCIES = {
		'system': [
			'snips-hotword'
		],
		'pip': []
	}


	def onStop(self):
		super().onStop()
		self.Commons.runRootSystemCommand(['systemctl', 'stop', 'snips-hotword'])


	def onStart(self):
		super().onStart()
		self.Commons.runRootSystemCommand(['systemctl', 'start', 'snips-hotword'])
