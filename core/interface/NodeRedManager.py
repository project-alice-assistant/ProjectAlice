import json
import subprocess
from pathlib import Path

from core.base.model.Manager import Manager


class NodeRedManager(Manager):
	NAME = 'NodeRedManager'


	def __init__(self):
		super().__init__(self.NAME)
		self._nodes = dict()


	def onStart(self):
		super().onStart()
		self._nodes = self.SkillManager.allScenarioNodes()
		self.injectSkillNodes()
		subprocess.run(['sudo', 'systemctl', 'start', 'nodered'])


	def onStop(self):
		super().onStop()
		subprocess.run(['sudo', 'systemctl', 'stop', 'nodered'])


	@staticmethod
	def reloadServer():
		subprocess.run(['sudo', 'systemctl', 'restart', 'nodered'])


	def injectSkillNodes(self):
		if not self._nodes:
			return

		package = Path('../.node-red/package.json')
		if not package.exists():
			self.logWarning('Package json file for Node Red is missing. Is Node Red even installed?')
			return

		with package.open('r') as fp:
			data = json.load(fp)

		for nodeName, nodePath in self._nodes.items():
			if nodeName.rsplit('_', 1)[0] in data['dependencies']:
				continue

			subprocess.run(f'cd ~/.node-red && npm install {str(nodePath).rsplit("/", 1)[0]}', shell=True)
