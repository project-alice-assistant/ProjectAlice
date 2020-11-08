from flask import Flask, jsonify
from flask_cors import CORS

from core.base.model.Manager import Manager

app = Flask(__name__)


class WebUiManager(Manager):

	def __init__(self):
		super().__init__()
		app.config.from_object(__name__)


	def onStart(self):
		if not self.ConfigManager.getAliceConfigByName('webInterfaceActive'):
			self.logInfo('Web interface is disabled by settings')
			self.isActive = False
			return
		else:
			super().onStart()

		CORS(app, resources={r'/*': {'origins': '*'}})
		self.ThreadManager.newThread(
			name='WebInterface',
			target=app.run,
			kwargs={
				'debug'       : self.ConfigManager.getAliceConfigByName('debug'),
				'port'        : int(self.ConfigManager.getAliceConfigByName('webInterfacePort')),
				'host'        : '0.0.0.0',
				'use_reloader': False
			}
		)


@app.route('/ping', methods=['GET'])
def ping():
	return jsonify('pong')
