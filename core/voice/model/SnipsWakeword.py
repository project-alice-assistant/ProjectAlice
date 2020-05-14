from core.voice.model.WakewordEngine import WakewordEngine


class SnipsWakeword(WakewordEngine):

	NAME = 'Snips hotword'
	DEPENDENCIES = {
		'system': [
			'snips-hotword'
		],
		'pip': []
	}

	def __init__(self):
		super().__init__()


	def onBooted(self):
		super().onBooted()
		self.Commons.runRootSystemCommand(['systemctl', 'start', 'snips-hotword'])


	def onStop(self):
		self.Commons.runRootSystemCommand(['systemctl', 'stop', 'snips-hotword'])
