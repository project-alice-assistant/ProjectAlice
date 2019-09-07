import subprocess

import django
import os
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
		self._superManager.onBooted()

		if self._superManager.configManager.getAliceConfigByName('useSLC'):
			subprocess.run(['sudo', 'systemctl', 'start', 'snipsledcontrol'])


	@property
	def name(self) -> str:
		return self.NAME


	def onStop(self):
		self._logger.info('[ProjectAlice] Shutting down Project Alice')
		self._superManager.onStop()


	@staticmethod
	def _startDjango():
		os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.gui.settings')
		django.setup()
		management.call_command('runserver', '0:8000', '--noreload')
