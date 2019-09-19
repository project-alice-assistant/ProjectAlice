import os
import subprocess

import django
from django.core import management

from core.base.SuperManager import SuperManager
from core.commons.model.Singleton import Singleton


class ProjectAlice(Singleton):

	NAME = 'ProjectAlice'

	def __init__(self):
		Singleton.__init__(self, self.NAME)
		self._logger.info('Starting up project Alice core')
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
		self._logger.info('[ProjectAlice] Shutting down Project Alice')
		self._superManager.onStop()
