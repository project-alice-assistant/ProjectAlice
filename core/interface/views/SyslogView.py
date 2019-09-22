from pathlib import Path

from flask_classful import FlaskView
from flask import render_template

from core.commons import commons


class SyslogView(FlaskView):

	LOGS = Path(commons.rootDir(), 'var', 'logs', 'logs.log')

	def __init__(self):
		super().__init__()
		self._lastLine = 0

	def index(self):
		data = ['] -'.join(line.split('] -')[1:]) for line in self.getData()]
		return render_template('syslog.html', data=data)


	def getData(self):
		return self.LOGS.open('r').readlines()
