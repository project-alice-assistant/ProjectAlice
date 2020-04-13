import json
import logging
import string
import time
from pathlib import Path

import random
from flask import Flask, send_from_directory
from flask_login import LoginManager

from core.base.model.Manager import Manager
from core.interface.api.DialogApi import DialogApi
from core.interface.api.LoginApi import LoginApi
from core.interface.api.SkillsApi import SkillsApi
from core.interface.api.TelemetryApi import TelemetryApi
from core.interface.api.UsersApi import UsersApi
from core.interface.api.UtilsApi import UtilsApi
from core.interface.views.AdminAuth import AdminAuth
from core.interface.views.AdminView import AdminView
from core.interface.views.AliceWatchView import AliceWatchView
from core.interface.views.DevModeView import DevModeView
from core.interface.views.IndexView import IndexView
from core.interface.views.MyHomeView import MyHomeView
from core.interface.views.ScenarioView import ScenarioView
from core.interface.views.SkillsView import SkillsView
from core.interface.views.SyslogView import SyslogView


class WebInterfaceManager(Manager):
	app = Flask(__name__)
	app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

	_VIEWS = [AdminView, AdminAuth, IndexView, SkillsView, AliceWatchView, SyslogView, DevModeView, ScenarioView, MyHomeView]
	_APIS = [UtilsApi, LoginApi, UsersApi, SkillsApi, DialogApi, TelemetryApi]


	def __init__(self):
		super().__init__()
		log = logging.getLogger('werkzeug')
		log.setLevel(logging.ERROR)
		self._langData = dict()
		self._skillInstallProcesses = dict()
		self._flaskLoginManager = None


	# noinspection PyMethodParameters
	@app.route('/favicon.ico')
	def favicon():
		return send_from_directory('static/', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

	@app.route('/base/<path:filename>')
	def base_static(self, filename):
		return send_from_directory(self.app.root_path + '/../static/', filename)


	@property
	def langData(self) -> dict:
		return self._langData


	def onStart(self):
		super().onStart()
		if not self.ConfigManager.getAliceConfigByName('webInterfaceActive'):
			self.logInfo('Web interface is disabled by settings')
		else:
			langFile = Path(self.Commons.rootDir(), f'core/interface/languages/{self.LanguageManager.activeLanguage.lower()}.json')

			if not langFile.exists():
				self.logWarning(f'Lang **{self.LanguageManager.activeLanguage.lower()}** not found, falling back to **en**')
				langFile = Path(self.Commons.rootDir(), 'core/interface/languages/en.json')
			else:
				self.logInfo(f'Loaded interface in **{self.LanguageManager.activeLanguage.lower()}**')

			key = ''.join([random.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(20)])
			self.app.secret_key = key.encode()
			self._flaskLoginManager = LoginManager()
			self._flaskLoginManager.init_app(self.app)
			self._flaskLoginManager.user_loader(self.UserManager.getUserById)
			self._flaskLoginManager.login_view = '/adminAuth/'

			with langFile.open('r') as f:
				self._langData = json.load(f)

			for view in self._VIEWS:
				try:
					view.register(self.app)
				except Exception as e:
					self.logInfo(f'Exception while registering view: {e}')
					continue

			for api in self._APIS:
				try:
					api.register(self.app)
				except Exception as e:
					self.logInfo(f'Exception while registering api endpoint: {e}')
					continue

			self.ThreadManager.newThread(
				name='WebInterface',
				target=self.app.run,
				kwargs={
					'debug'       : self.ConfigManager.getAliceConfigByName('debug'),
					'port'        : int(self.ConfigManager.getAliceConfigByName('webInterfacePort')),
					'host'        : self.Commons.getLocalIp(),
					'use_reloader': False
				}
			)


	def onStop(self):
		self.ThreadManager.terminateThread('WebInterface')


	def newSkillInstallProcess(self, skill):
		self._skillInstallProcesses[skill] = {
			'startedAt': time.time(),
			'status'   : 'installing'
		}


	def onSkillUpdated(self, skill: str):
		try:
			if skill in self.skillInstallProcesses:
				self.skillInstallProcesses[skill]['status'] = 'updated'
		except KeyError as e:
			self.logError(f'Failed setting skill **{skill}** status to **updated**: {e}')


	def onSkillInstalled(self, skill: str):
		try:
			if skill in self.skillInstallProcesses:
				self.skillInstallProcesses[skill]['status'] = 'installed'
		except KeyError as e:
			self.logError(f'Failed setting skill **{skill}** status to **installed**: {e}')


	def onSkillInstallFailed(self, skill: str):
		try:
			if skill in self.skillInstallProcesses:
				self.skillInstallProcesses[skill]['status'] = 'failed'
		except KeyError as e:
			self.logError(f'Failed setting skill **{skill}** status to **failed**: {e}')


	@property
	def skillInstallProcesses(self) -> dict:
		return self._skillInstallProcesses


	@property
	def flaskLoginManager(self) -> LoginManager:
		return self._flaskLoginManager
