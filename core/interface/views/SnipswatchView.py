import subprocess
from pathlib import Path

from flask import jsonify, render_template

from core.base.SuperManager import SuperManager
from core.interface.views.View import View


class SnipswatchView(View):

	def __init__(self):
		super().__init__()
		self._counter = 0
		self._thread = None
		self._file = Path('/tmp/snipswatch.txt')
		self._thread = None

		if self._file.exists():
			subprocess.run(['sudo', 'rm', self._file])


	def index(self):
		return render_template('snipswatch.html', langData=self._langData)


	def startWatching(self):
		process = subprocess.Popen('snips-watch -vv --html', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

		flag = SuperManager.getInstance().threadManager.newLock('running')
		flag.set()
		while flag.isSet():
			out = process.stdout.readline().decode()
			if out:
				with self._file.open('a+') as fp:
					line = out.replace('<b><font color=#009900>', '<b><font color="green">').replace('#009900', '"yellow"').replace('#0000ff', '"green"')
					fp.write(line)


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
		return self.update()


	def _getData(self) -> list:
		try:
			data = self._file.open('r').readlines()
			ret = data[self._counter:]
			self._counter = len(data)
			return ret
		except:
			return list()
