import json
import logging
from pathlib import Path

from flask import Flask, send_from_directory

from core.base.model.Manager import Manager
from core.commons import commons
from core.interface.views.AdminView import AdminView
from core.interface.views.IndexView import IndexView
from core.interface.views.ModulesView import ModulesView
from core.interface.views.SnipswatchView import SnipswatchView
from core.interface.views.SyslogView import SyslogView


class WebInterfaceManager(Manager):

	NAME = 'WebInterfaceManager'
	app = Flask(__name__)

	def __init__(self):
		super().__init__(self.NAME)
		log = logging.getLogger('werkzeug')
		log.setLevel(logging.ERROR)
		self._langData = dict()


	@app.route('/base/<path:filename>')
	def base_static(self, filename):
		return send_from_directory(self.app.root_path + '/../static/', filename)


	@property
	def langData(self) -> dict:
		return self._langData


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('webInterfaceActive'):
			self._logger.info(f'[{self.name}] Web interface is disabled by settings')
		else:
			langFile = Path(commons.rootDir(), f'core/interface/languages/{self.LanguageManager.activeLanguage.lower()}.json')

			if not langFile.exists():
				self._logger.warning(f'[{self.name}] Lang "{self.LanguageManager.activeLanguage.lower()}" not found, falling back to "en"')
				langFile = Path(commons.rootDir(), 'core/interface/languages/en.json')
			else:
				self._logger.info(f'[{self.name}] Loaded interface in "{self.LanguageManager.activeLanguage.lower()}"')

			with langFile.open('r') as f:
				self._langData = json.load(f)

			IndexView.register(self.app)
			ModulesView.register(self.app)
			SyslogView.register(self.app)
			SnipswatchView.register(self.app)
			AdminView.register(self.app)

			self.ThreadManager.newThread(
				name='WebInterface',
				target=self.app.run,
				kwargs={
					'debug': True,
					'port': int(self.ConfigManager.getAliceConfigByName('webInterfacePort')),
					'host': commons.getLocalIp(),
					'use_reloader': False
				}
			)
