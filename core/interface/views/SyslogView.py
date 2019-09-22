from pathlib import Path

from flask_classful import FlaskView
from flask import render_template, jsonify

from core.commons import commons


class SyslogView(FlaskView):

	LOGS = Path(commons.rootDir(), 'var', 'logs', 'logs.log')

	def __init__(self):
		super().__init__()
		self._lastLine = 0
		self._counter = 0


	def index(self):
		return render_template('syslog.html')


	def update(self):
		return jsonify(data=self._getData())


	def _getData(self) -> list:
		data = self.LOGS.open('r').readlines()
		ret = data[self._counter:]
		self._counter = len(data)
		return ['] -'.join(line.split('] -')[1:]) for line in ret]
