from core.base.SuperManager import SuperManager
from core.commons.model.Singleton import Singleton
from core.util.Stopwatch import Stopwatch


class ProjectAlice(Singleton):

	NAME = 'ProjectAlice'

	def __init__(self, restartHandler: callable):
		Singleton.__init__(self, self.NAME)
		self.logInfo('Starting up Project Alice')
		self._booted = False
		with Stopwatch() as stopWatch:
			self._restart = False
			self._restartHandler = restartHandler
			self._superManager = SuperManager(self)

			self._superManager.initManagers()
			self._superManager.onStart()

			if self._superManager.configManager.getAliceConfigByName('useSLC'):
				self._superManager.commons.runRootSystemCommand(['systemctl', 'start', 'snipsledcontrol'])

			self._superManager.onBooted()
		self.logInfo(f'- Started Project Alice in {stopWatch} seconds')
		self._booted = True


	@property
	def name(self) -> str:
		return self.NAME


	@property
	def isBooted(self) -> bool:
		return self._booted


	@property
	def restart(self) -> bool:
		return self._restart


	@restart.setter
	def restart(self, value: bool):
		self._restart = value


	def doRestart(self):
		self._restart = True
		self.onStop()


	def onStop(self):
		self.logInfo('Shutting down Project Alice')
		self._superManager.onStop()
		if self._superManager.configManager.getAliceConfigByName('useSLC'):
			self._superManager.commons.runRootSystemCommand(['systemctl', 'stop', 'snipsledcontrol'])

		self.INSTANCE = None
		self._restartHandler()
