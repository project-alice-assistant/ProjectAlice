#  Copyright (c) 2021
#
#  This file, WebUIManager.py, is part of Project Alice.
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

from pathlib import Path

import psutil as psutil

from core.base.model.Manager import Manager
from core.commons import constants


class WebUIManager(Manager):

	def onStart(self):
		super().onStart()

		if not self.ConfigManager.getAliceConfigByName('webInterfaceActive'):
			self.logInfo('Web interface is disabled by settings')
			self.isActive = False
		else:
			try:
				self.startWebserver()
				if self.ConfigManager.getAliceConfigByName('displaySystemUsage'):
					self.ThreadManager.newThread(
						name='DisplayResourceUsage',
						target=self.publishResourceUsage
					)
			except Exception as e:
				self.logWarning(f'WebUI starting failed: {e}')
				self.onStop()


	def publishResourceUsage(self):
		self.MqttManager.publish(
			topic=constants.TOPIC_RESOURCE_USAGE,
			payload={
				'cpu': psutil.cpu_percent(),
				'ram': psutil.virtual_memory().percent,
				'swp': psutil.swap_memory().percent
			}
		)
		self.ThreadManager.doLater(interval=1, func=self.publishResourceUsage)


	def setConfFile(self) -> bool:
		try:
			self.Commons.createFileFromTemplate(
				templateFile=Path('system/nginx/default.j2'),
				dest=Path('/etc/nginx/sites-enabled/default'),
				listen='0.0.0.0:',
				port=str(self.ConfigManager.getAliceConfigByName('webInterfacePort')),
				root=f'{self.Commons.rootDir()}/core/webui/public/'
			)
			return True
		except Exception as e:
			self.logError(f'Something went wrong setting configuration file: {e}')
			return False


	def onStop(self):
		super().onStop()
		self.stopWebserver()


	def restart(self):
		if not self.isActive:
			return

		self.stopWebserver()
		self.startWebserver()


	def stopWebserver(self):
		status = self.Commons.runRootSystemCommand('systemctl stop nginx')
		if status.returncode != 0:
			self.logWarning(f'Nginx stopping failed. Is it even installed?')
		self.logInfo('Stopped nginx server')


	def startWebserver(self):
		if not self.setConfFile():
			return

		status = self.Commons.runRootSystemCommand('systemctl start nginx')
		if status.returncode != 0:
			raise Exception(f'Nginx starting failed. Is it even installed?')

		self.logInfo('Started nginx server')
