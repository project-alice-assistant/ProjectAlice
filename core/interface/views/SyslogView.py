from pathlib import Path

from flask_classful import FlaskView, route
from flask import render_template

from core.commons import commons


class SyslogView(FlaskView):

	LOGS = Path(commons.rootDir(), 'var', 'logs', 'logs.log')

	def __init__(self):
		super().__init__()
		self._lastLine = 0

	def index(self):
		data = ['] -'.join(line.split('] -')[1:]) for line in self._getData()]
		return render_template('syslog.html', data=data)


	@route('/update')
	def update(self):
		return self._getData()


	def _getData(self):
		return self.LOGS.open('r').readlines()
