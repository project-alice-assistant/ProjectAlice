import time

import subprocess

from flask_classful import FlaskView
from flask import render_template, jsonify

from core.base.SuperManager import SuperManager


class SnipswatchView(FlaskView):

	def __init__(self):
		super().__init__()
		self._counter = 0
		self._watch = list()
		self._thread = None


	def index(self):
		return render_template('snipswatch.html')


	def startWatching(self):
		process = subprocess.Popen('snips-watch -vv', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

		while True:
			out = process.stdout.readline().decode()
			if out != '':
				self._watch.append(out.strip())
			time.sleep(0.1)


	def update(self):
		return jsonify(data=self._getData())


	def refresh(self):
		self._thread = SuperManager.getInstance().threadManager.newThread(
			name='snipswatch',
			target=self.startWatching,
			autostart=True
		)

		self._counter = 0
		return jsonify(data=self._getData())


	def _getData(self) -> list:
		data = self._watch.copy()
		ret = data[self._counter:]
		self._counter = len(data)
		return ret
