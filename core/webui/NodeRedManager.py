#  Copyright (c) 2021
#
#  This file, NodeRedManager.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:49 CEST

import json
import os
import shutil
import time
from pathlib import Path
from subprocess import PIPE, Popen

from core.base.model.Manager import Manager
from core.webui.model.UINotificationType import UINotificationType


class NodeRedManager(Manager):
	PACKAGE_PATH = Path('../.node-red/package.json')
	DEFAULT_NODES_ACTIVE = {
		'node-red': [
			'debug',
			'JSON',
			'split',
			'sort',
			'function',
			'change',
			'inject',
			'delay',
			'mqtt',
			'switch',
			'trigger',
			'template'
		]
	}


	def __init__(self):
		super().__init__()


	def onStart(self):
		self.isActive = self.ConfigManager.getAliceConfigByName('scenariosActive')

		if not self.isActive:
			return

		super().onStart()

		if not self.PACKAGE_PATH.exists():
			self.isActive = False
			self.install()
			return

		self.injectSkillNodes()
		self.Commons.runRootSystemCommand(['systemctl', 'start', 'nodered'])


	def install(self):
		self.logInfo('Node-RED not found, installing, this might take a while...')
		self.WebUINotificationManager.newNotification(typ=UINotificationType.INFO, notification='installNodeRed', key='nodered')
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
			self.logError('Failed installing Node-RED')
			self.WebUINotificationManager.newNotification(typ=UINotificationType.ERROR, notification='failedInstallNodeRed', key='nodered')
			self.onStop()
			return

		process.stdin.close()
		returnCode = process.wait(timeout=900)

		if returnCode:
			self.logError('Failed installing Node-red')
			self.WebUINotificationManager.newNotification(typ=UINotificationType.ERROR, notification='failedInstallNodeRed', key='nodered')
			self.onStop()
		else:
			self.logInfo('Successfully installed Node-red')
			self.configureNewNodeRed()
			self.onStart()


	def configureNewNodeRed(self):
		self.logInfo('Configuring')
		# Start to generate base configs and stop it after
		self.Commons.runRootSystemCommand(['systemctl', 'start', 'nodered'])
		time.sleep(5)
		self.Commons.runRootSystemCommand(['systemctl', 'stop', 'nodered'])
		time.sleep(3)
		config = Path(self.PACKAGE_PATH.parent, '.config.nodes.json')
		data = json.loads(config.read_text())
		for package in data.values():
			keeper = self.DEFAULT_NODES_ACTIVE.get(package['name'], list())
			for node in package['nodes'].values():
				if node['name'] in keeper:
					continue
				node['enabled'] = False

		config.write_text(json.dumps(data))
		self.logInfo('Nodes configured')
		self.logInfo('Applying Project Alice settings')

		self.Commons.runSystemCommand('npm install --prefix ~/.node-red @node-red-contrib-themes/midnight-red'.split(), shell=True)
		shutil.copy(Path('system/node-red/settings.js'), Path(os.path.expanduser('~/.node-red'), 'settings.js'))
		self.logInfo("All done, let's start all this")
		self.WebUINotificationManager.newNotification(typ=UINotificationType.INFO, notification='installedNodeRed', key='nodered')


	def onStop(self):
		super().onStop()
		if not self.ConfigManager.getAliceConfigByName('dontStopNodeRed'):
			self.Commons.runRootSystemCommand(['systemctl', 'stop', 'nodered'])


	def toggle(self):
		if self.isActive:
			self.onStop()
		else:
			self.onStart()


	def reloadServer(self):
		self.Commons.runRootSystemCommand(['systemctl', 'restart', 'nodered'])


	def onSkillDeleted(self, skill: str):
		if not self.PACKAGE_PATH.exists() or not self.SkillManager.skillScenarioNode(skillName=skill):
			return

		uninstall = self.Commons.runSystemCommand(f'cd ~/.node-red && npm uninstall {self.SkillManager.skillScenarioNode(skillName=skill)}', shell=True)
		if uninstall.returncode == 1:
			self.logWarning(f'Something went wrong uninstalling node for skill {skill}: {uninstall.stderr}')
		else:
			self.reloadServer()


	def injectSkillNodes(self):
		restart = False

		if not self.PACKAGE_PATH.exists():
			self.logWarning('Package json file for Node-RED is missing. Is Node-RED even installed?')
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
