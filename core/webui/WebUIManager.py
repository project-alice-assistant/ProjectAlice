from pathlib import Path

import psutil as psutil

from core.base.model.Manager import Manager
from core.commons import constants


class WebUIManager(Manager):

	def __init__(self):
		super().__init__()


	def onStart(self):
		super().onStart()

		if not self.ConfigManager.getAliceConfigByName('webInterfaceActive'):
			self.logInfo('Web interface is disabled by settings')
			self.isActive = False
		else:
			self.startWebserver()
			if self.ConfigManager.getAliceConfigByName('displaySystemUsage'):
				self.ThreadManager.newThread(
					name='DisplayResourceUsage',
					target=self.publishResourceUsage
				)


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
		self.Commons.runRootSystemCommand('systemctl stop nginx'.split())
		self.logInfo('Stopped nginx server')


	def startWebserver(self):
		if not self.setConfFile():
			return

		self.Commons.runRootSystemCommand('systemctl start nginx'.split())
		self.logInfo('Started nginx server')
