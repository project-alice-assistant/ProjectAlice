from flask import Flask

from core.base.model.Manager import Manager
from core.commons import commons
from core.interface.views.AdminView import AdminView
from core.interface.views.IndexView import IndexView
from core.interface.views.ModulesView import ModulesView
from core.interface.views.SnipswatchView import SnipswatchView
from core.interface.views.SyslogView import SyslogView
import logging


class WebInterfaceManager(Manager):

	NAME = 'WebInterfaceManager'
	app = Flask(__name__)

	def __init__(self):
		super().__init__(self.NAME)
		log = logging.getLogger('werkzeug')
		log.setLevel(logging.ERROR)


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('webInterfaceActive'):
			self._logger.info('[{}] Web interface is disabled by settings'.format(self.name))
		else:
			IndexView.register(self.app)
			ModulesView.register(self.app)
			SyslogView.register(self.app)
			SnipswatchView.register(self.app)
			AdminView.register(self.app)

			self.ThreadManager.newThread(
				name='WebInterface',
				target=self.app.run,
				kwargs={
					'debug': False,
					'port': int(self.ConfigManager.getAliceConfigByName('webInterfacePort')),
					'host': commons.getLocalIp(),
					'use_reloader': False
				}
			)
