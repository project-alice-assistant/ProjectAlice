from pathlib import Path

import psutil as psutil

from core.base.model.Manager import Manager
from core.commons import constants
from core.webui.model.UINotificationType import UINotificationType


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


	def newNotification(self, tipe: UINotificationType, notification: str, key: str = None, replaceTitle: list = None, replaceBody: list = None):
		"""
		Sends a UI notification
		:param tipe: The notification type
		:param notification: the json object key of the notification to send
		:param key: A notification key. If provided, it will be used on the UI as div id. It's usefull for notifications that get updated over time
		:param replaceTitle: A list of strings to format the original title string
		:param replaceBody: A list of strings to format the original body string
		:return:
		"""

		notification = self.LanguageManager.getWebUINotification(notification)
		if not notification:
			return

		title = notification['title']
		if replaceTitle:
			title = title.format(replaceTitle)

		body = notification['body']
		if replaceBody:
			body = body.format(*replaceBody)

		self.MqttManager.publish(topic=constants.TOPIC_UI_NOTIFICATION, payload={
			'type': tipe.value,
			'title': title,
			'text': body,
			'key': key
		})
