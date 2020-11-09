import logging
import random
import string

from flask import Flask
from flask_cors import CORS

from core.base.model.Manager import Manager

app = Flask(__name__)


class ApiManager(Manager):

	def __init__(self):
		super().__init__()
		log = logging.getLogger('werkzeug')
		log.setLevel(logging.ERROR)

		app.config.from_object(__name__)
		key = ''.join([random.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(20)])
		app.secret_key = key.encode()


	def onStart(self):
		super().onStart()
		CORS(app, resources={r'/*': {'origins': '*'}})


	def restart(self):
		self.ThreadManager.terminateThread('API')
		self.startThread()


	def startThread(self):
		if not self.isActive:
			return

		self.ThreadManager.newThread(
			name='API',
			target=app.run,
			kwargs={
				'debug'       : self.ConfigManager.getAliceConfigByName('debug'),
				'port'        : int(self.ConfigManager.getAliceConfigByName('apiPort')),
				'host'        : '0.0.0.0',
				'use_reloader': False
			}
		)
