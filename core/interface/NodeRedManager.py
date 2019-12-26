import json
from pathlib import Path

from core.base.model.Manager import Manager
from core.base.model.Version import Version


class NodeRedManager(Manager):

	def __init__(self):
		super().__init__()


	def onStart(self):
		super().onStart()
		self.injectSkillNodes()
		self.Commons.runRootSystemCommand(['systemctl', 'start', 'nodered'])


	def onStop(self):
		super().onStop()
		self.Commons.runRootSystemCommand(['systemctl', 'stop', 'nodered'])


	def reloadServer(self):
		self.Commons.runRootSystemCommand(['systemctl', 'restart', 'nodered'])


	def injectSkillNodes(self):
		package = Path('../.node-red/package.json')
		if not package.exists():
			self.logWarning('Package json file for Node Red is missing. Is Node Red even installed?')
			return

		for skillName, tup in self.SkillManager.allScenarioNodes().items():
			path = Path('../.node-red/node_modules', tup[0], 'package.json')
			if not path.exists():
				self.logInfo('New scenario node found')
				install = self.Commons.runSystemCommand(f'cd ~/.node-red && npm install {tup[2]}', shell=True)
				if install.returncode == 1:
					self.logWarning(f'Something went wrong installing new node: {install.stderr}')

				continue

			with path.open('r') as fp:
				data = json.load(fp)
				version = Version(data['version'])

				if version < tup[1]:
					self.logInfo('New scenario node update found')
					install = self.Commons.runSystemCommand(f'cd ~/.node-red && npm install {tup[2]}', shell=True)
					if install.returncode == 1:
						self.logWarning(f'Something went wrong updating node: {install.stderr}')
