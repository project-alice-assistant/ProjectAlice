import logging
import random
import string

from flask import Flask
from flask_cors import CORS

from core.base.model.Manager import Manager
from core.webApi.model.DialogApi import DialogApi
from core.webApi.model.LoginApi import LoginApi
from core.webApi.model.SkillsApi import SkillsApi
from core.webApi.model.TelemetryApi import TelemetryApi
from core.webApi.model.UsersApi import UsersApi
from core.webApi.model.UtilsApi import UtilsApi


class ApiManager(Manager):
	app = Flask(__name__)
	app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
	CORS(app, resources={r'/api/*': {'origins': '*'}})

	_APIS = [UtilsApi, LoginApi, UsersApi, SkillsApi, DialogApi, TelemetryApi]


	def __init__(self):
		super().__init__()
		log = logging.getLogger('werkzeug')
		log.setLevel(logging.ERROR)


	def onStart(self):
		super().onStart()

		key = ''.join([random.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(20)])
		self.app.secret_key = key.encode()
		self.app.cors_headers = 'Content-Type'

		for api in self._APIS:
			try:
				api.register(self.app)
			except Exception as e:
				self.logInfo(f'Exception while registering api endpoint: {e}')
				continue

		self.startThread()


	def restart(self):
		self.ThreadManager.terminateThread('API')
		self.startThread()


	def startThread(self):
		if not self.isActive:
			return

		self.ThreadManager.newThread(
			name='API',
			target=self.app.run,
			kwargs={
				'debug'       : self.ConfigManager.getAliceConfigByName('debug'),
				'port'        : int(self.ConfigManager.getAliceConfigByName('apiPort')),
				'host'        : '0.0.0.0',
				'use_reloader': False
			}
		)
