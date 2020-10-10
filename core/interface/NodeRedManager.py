from pathlib import Path
from subprocess import PIPE, Popen

from core.base.model.Manager import Manager


class NodeRedManager(Manager):

	PACKAGE_PATH = Path('../.node-red/package.json')

	def __init__(self):
		super().__init__()


	def onStart(self):
		self.isActive = self.ConfigManager.getAliceConfigByName('scenariosActive')

		if not self.isActive:
			return

		super().onStart()

		if not self.PACKAGE_PATH.exists():
			self.ThreadManager.newThread(name='installNodered', target=self.install)
			return

		self.injectSkillNodes()
		self.Commons.runRootSystemCommand(['systemctl', 'start', 'nodered'])


	def install(self):
		self.logInfo('Node red not found, installing, this might take a while...')
		self.Commons.downloadFile(
			url='https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered',
			dest='var/cache/node-red.sh'
		)
		self.Commons.runRootSystemCommand('chmod +x var/cache/node-red.sh'.split())

		process = Popen('./var/cache/node-red.sh'.split(), stdin=PIPE, stdout=PIPE)
		try:
			process.stdin.write(b'y\n')
			process.stdin.write(b'n\n')
		except IOError:
			self.logError('Failed installing Node-red')
			self.onStop()
			return

		process.stdin.close()
		returnCode = process.wait(timeout=120)

		if returnCode:
			self.logError('Failed installing Node-red')
			self.onStop()
		else:
			self.logInfo('Succesfully installed Node-red')
			self.onStart()


	def onStop(self):
		if not self.isActive:
			return

		super().onStop()
		self.Commons.runRootSystemCommand(['systemctl', 'stop', 'nodered'])


	def toggle(self):
		if self.isActive:
			self.onStop()
		else:
			self.onStart()


	def reloadServer(self):
		self.Commons.runRootSystemCommand(['systemctl', 'restart', 'nodered'])


	def injectSkillNodes(self):
		restart = False

		if not self.PACKAGE_PATH.exists():
			self.logWarning('Package json file for Node Red is missing. Is Node Red even installed?')
			self.onStop()
			return

		for skillName, tup in self.SkillManager.allScenarioNodes().items():
			scenarioNodeName, scenarioNodeVersion, scenarioNodePath = tup
			path = Path('../.node-red/node_modules', scenarioNodeName, 'package.json')
			if not path.exists():
				self.logInfo(f'New scenario node found for skill **{skillName}**: {scenarioNodeName}')
				install = self.Commons.runSystemCommand(f'cd ~/.node-red && npm install {scenarioNodePath}', shell=True)
				if install.returncode == 1:
					self.logWarning(f'Something went wrong installing new node **{scenarioNodeName}**: {install.stderr}')
				else:
					restart = True

				continue

			version = self.SkillManager.getSkillScenarioVersion(skillName)

			if version < scenarioNodeVersion:
				self.logInfo(f'New scenario update found for node **{scenarioNodeName}**')
				install = self.Commons.runSystemCommand(f'cd ~/.node-red && npm install {scenarioNodePath}', shell=True)
				if install.returncode == 1:
					self.logWarning(f'Something went wrong updating node **{scenarioNodeName}**: {install.stderr}')
					continue

				self.DatabaseManager.update(
					tableName='skills',
					callerName=self.SkillManager.name,
					values={
						'scenarioVersion': str(scenarioNodeVersion)
					},
					row=('skillName', skillName)
				)
				restart = True

		if restart:
			self.reloadServer()
