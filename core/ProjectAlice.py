import subprocess

from core.base.SuperManager import SuperManager
from core.commons.model.Singleton import Singleton


class ProjectAlice(Singleton):

	NAME = 'ProjectAlice'

	def __init__(self):
		Singleton.__init__(self, self.NAME)
		self.logInfo('Starting up project Alice core')
		self._superManager = SuperManager(self)

		self._superManager.initManagers()
		self._superManager.onStart()

		if self._superManager.configManager.getAliceConfigByName('useSLC'):
			subprocess.run(['sudo', 'systemctl', 'start', 'snipsledcontrol'])

		self._superManager.onBooted()


	@property
	def name(self) -> str:
		return self.NAME


	def onStop(self):
		self.logInfo('[ProjectAlice] Shutting down Project Alice')
		self._superManager.onStop()
		if self._superManager.configManager.getAliceConfigByName('useSLC'):
			subprocess.run(['sudo', 'systemctl', 'stop', 'snipsledcontrol'])
