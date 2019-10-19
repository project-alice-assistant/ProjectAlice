from pathlib import Path

from flask import jsonify, render_template

from core.commons import Commons
from core.interface.views.View import View


class SyslogView(View):
	LOGS = Path(self.Commons.rootDir(), 'var', 'logs', 'logs.log')


	def __init__(self):
		super().__init__()
		self._counter = 0


	def index(self):
		return render_template('syslog.html', langData=self._langData, devMode=self.ConfigManager.getAliceConfigByName('webInterfaceDevMode'))


	def update(self):
		return jsonify(data=self._getData())


	def refresh(self):
		self._counter = 0
		return self.update()


	def _getData(self) -> list:
		data = self.LOGS.open('r').readlines()
		ret = data[self._counter:]
		self._counter = len(data)
		return ['] -'.join(line.split('] -')[2:]) for line in ret]
