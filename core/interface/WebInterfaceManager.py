import json
import logging
import time
from pathlib import Path

from flask import Flask, send_from_directory

from core.base.model.Manager import Manager
from core.commons import commons
from core.interface.views.AdminView import AdminView
from core.interface.views.IndexView import IndexView
from core.interface.views.ModulesView import ModulesView
from core.interface.views.SnipswatchView import SnipswatchView
from core.interface.views.SyslogView import SyslogView
from core.interface.views.DevModeView import DevModeView


class WebInterfaceManager(Manager):

	NAME = 'WebInterfaceManager'
	app = Flask(__name__)

	_VIEWS = [AdminView, IndexView, ModulesView, SnipswatchView, SyslogView, DevModeView]

	def __init__(self):
		super().__init__(self.NAME)
		log = logging.getLogger('werkzeug')
		log.setLevel(logging.ERROR)
		self._langData = dict()
		self._moduleInstallProcesses = dict()


	@app.route('/base/<path:filename>')
	def base_static(self, filename):
		return send_from_directory(self.app.root_path + '/../static/', filename)


	@property
	def langData(self) -> dict:
		return self._langData


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('webInterfaceActive'):
			self.logInfo(f'Web interface is disabled by settings')
		else:
			langFile = Path(commons.rootDir(), f'core/interface/languages/{self.LanguageManager.activeLanguage.lower()}.json')

			if not langFile.exists():
				self.logWarning(f'Lang "{self.LanguageManager.activeLanguage.lower()}" not found, falling back to "en"')
				langFile = Path(commons.rootDir(), 'core/interface/languages/en.json')
			else:
				self.logInfo(f'Loaded interface in "{self.LanguageManager.activeLanguage.lower()}"')

			with langFile.open('r') as f:
				self._langData = json.load(f)

			for view in self._VIEWS:
				view.register(self.app)

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


	def newModuleInstallProcess(self, module):
		self._moduleInstallProcesses[module] = {
			'startedAt': time.time(),
			'status'   : 'installing'
		}


	def onModuleInstalled(self, **kwargs):
		module = ''
		try:
			module = kwargs['module']
			if module in self.moduleInstallProcesses:
				self.moduleInstallProcesses[module]['status'] = 'installed'
		except Exception as e:
			self.logError(f'Failed setting module "{module}" status to "installed": {e}')


	def onModuleInstallFailed(self, **kwargs):
		module = ''
		try:
			module = kwargs['module']
			if module in self.moduleInstallProcesses:
				self.moduleInstallProcesses[module]['status'] = 'failed'
		except Exception as e:
			self.logError(f'Failed setting module "{module}" status to "failed": {e}')


	@property
	def moduleInstallProcesses(self) -> dict:
		return self._moduleInstallProcesses
