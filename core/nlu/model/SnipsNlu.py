from core.base.SuperManager import SuperManager
from core.nlu.model.NluEngine import NluEngine


class SnipsNlu(NluEngine):
	NAME = 'Snips NLU'


	def __init__(self):
		super().__init__()


	def start(self):
		super().start()
		SuperManager.getInstance().snipsServicesManager.runCmd(cmd='start', services=['snips-nlu'])


	def stop(self):
		super().stop()
		SuperManager.getInstance().snipsServicesManager.runCmd(cmd='stop', services=['snips-nlu'])
