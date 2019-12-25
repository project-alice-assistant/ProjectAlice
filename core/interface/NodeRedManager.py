import subprocess

from core.base.model.Manager import Manager


class NodeRedManager(Manager):
	NAME = 'NodeRedManager'


	def __init__(self):
		super().__init__(self.NAME)


	def onStart(self):
		super().onStart()
		subprocess.run(['sudo', 'systemctl', 'start', 'nodered'])


	def onStop(self):
		super().onStart()
		subprocess.run(['sudo', 'systemctl', 'stop', 'nodered'])


	@staticmethod
	def reloadServer():
		subprocess.run(['sudo', 'systemctl', 'restart', 'nodered'])
