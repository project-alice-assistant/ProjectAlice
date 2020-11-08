import logging
import random
import string

from flask import Flask, render_template, send_from_directory
from flask_cors import CORS

from core.base.model.Manager import Manager

app = Flask(__name__)


class WebUiManager(Manager):

	def __init__(self):
		super().__init__()
		log = logging.getLogger('werkzeug')
		log.setLevel(logging.ERROR)

		app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
		app.config.from_object(__name__)
		key = ''.join([random.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(20)])
		app.secret_key = key.encode()


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


# noinspection PyMethodParameters
@app.route('/favicon.ico')
def favicon():
	return send_from_directory('static/', 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/base/<path:filename>')
def base_static(self, filename):
	return send_from_directory(self.app.root_path + '/../static/', filename)


@app.route('/', methods=['GET'])
def index():
	return render_template(template_name_or_list='index.html')
