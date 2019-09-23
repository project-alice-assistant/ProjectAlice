import time
from pathlib import Path

import subprocess

from flask_classful import FlaskView
from flask import render_template, jsonify

from core.base.SuperManager import SuperManager
from core.commons import commons


class SnipswatchView(FlaskView):

	def __init__(self):
		super().__init__()
		self._counter = 0
		self._thread = None
		self._file = Path('/tmp/snipswatch.txt')
		self._thread = None

		if self._file.exists():
			subprocess.run(['sudo', 'rm', self._file])


	def index(self):
		return render_template('snipswatch.html')


	def startWatching(self):
		process = subprocess.Popen('snips-watch -vv', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

		while True:
			out = process.stdout.readline().decode()
			if out != '':
				with self._file.open('a+') as f:
					f.write(commons.escapeAnsi(out))


	def update(self):
		return jsonify(data=self._getData())


	def refresh(self):
		if not self._thread:
			self._thread = SuperManager.getInstance().threadManager.newThread(
				name='snipswatch',
				target=self.startWatching,
				autostart=True
			)

		self._counter = 0
		return jsonify(data=self._getData())


	def _getData(self) -> list:
		try:
			data = self._file.open('r').readlines()
			ret = data[self._counter:]
			self._counter = len(data)
			return ret
		except:
			return list()
