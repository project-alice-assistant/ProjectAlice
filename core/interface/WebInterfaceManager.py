import json
import logging
from pathlib import Path

from flask import Flask

from core.base.model.Manager import Manager
from core.commons import commons
from core.interface.model.WidgetInfo import WidgetInfo
from core.interface.views.AdminView import AdminView
from core.interface.views.IndexView import IndexView
from core.interface.views.ModulesView import ModulesView
from core.interface.views.SnipswatchView import SnipswatchView
from core.interface.views.SyslogView import SyslogView


class WebInterfaceManager(Manager):

	NAME = 'WebInterfaceManager'
	app = Flask(__name__)


	DATABASE = {
		'widgets': [
			'parent TEXT NOT NULL UNIQUE',
			'name TEXT NOT NULL UNIQUE',
			'posx INTEGER NOT NULL',
			'posy INTEGER NOT NULL',
			'state TEXT NOT NULL',
			'size TEXT NOT NULL',
			'options TEXT NOT NULL'
		]
	}


	def __init__(self):
		super().__init__(self.NAME, self.DATABASE)
		log = logging.getLogger('werkzeug')
		log.setLevel(logging.ERROR)
		self._langData = dict()
		self._widgetsInfo = dict()


	@property
	def langData(self) -> dict:
		return self._langData


	@property
	def widgets(self) -> dict:
		return self._widgetsInfo


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('webInterfaceActive'):
			self._logger.info('[{}] Web interface is disabled by settings'.format(self.name))
		else:
			langFile = Path('{}/core/interface/languages/{}.json'.format(commons.rootDir(), self.LanguageManager.activeLanguage.lower()))

			if not langFile.exists():
				self._logger.warning('[{}] Lang "{}" not found, falling back to "en"'.format(self.name, self.LanguageManager.activeLanguage.lower()))
				langFile = Path('{}/core/interface/languages/en.json'.format(commons.rootDir()))
			else:
				self._logger.info('[{}] Loaded interface in "{}"'.format(self.name, self.LanguageManager.activeLanguage.lower()))

			with langFile.open('r') as f:
				self._langData = json.load(f)

			self._loadWidgets()
			self._logger.info('[{}] Loaded {} widgets'.format(self.name, len(self._widgetsInfo.keys())))

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


	def _loadWidgets(self):
		widgets = self.databaseFetch(
			tableName='widgets',
			method='all'
		)

		for widget in widgets:
			self._widgetsInfo['{}_{}'.format(widget['parent'], widget['name'])] = WidgetInfo(widget)
