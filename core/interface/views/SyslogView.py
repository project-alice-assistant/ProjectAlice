from pathlib import Path

from flask import jsonify, render_template

from core.interface.views.View import View


class SyslogView(View):
	route_base = '/syslog/'
	counter = 0

	def __init__(self):
		super().__init__()
		self._logs = Path(self.Commons.rootDir(), 'var', 'logs', 'logs.log')


	def index(self):
		return render_template('syslog.html',
		                       langData=self._langData,
		                       devMode=self.ConfigManager.getAliceConfigByName('webInterfaceDevMode'),
		                       updateChannel=self.ConfigManager.getAliceConfigByName('updateChannel'))


	@classmethod
	def setCounter(cls, value: int):
		cls.counter = value


	@classmethod
	def getCounter(cls) -> int:
		return cls.counter


	def update(self):
		return jsonify(data=self._getData())


	def refresh(self):
		self.__class__.setCounter(0)
		return self.update()


	def _getData(self) -> list:
		data = self._logs.open('r').readlines()
		ret = data[self.__class__.getCounter():]
		self.__class__.setCounter(len(data))
		return ['] -'.join(line.split('] -')[2:]) for line in ret]
