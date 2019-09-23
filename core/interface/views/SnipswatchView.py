import re
import subprocess
from pathlib import Path

from flask import jsonify, render_template

from core.base.SuperManager import SuperManager
from core.commons import commons
from core.interface.views.View import View

from ansi2html import Ansi2HTMLConverter


class SnipswatchView(View):

	def __init__(self):
		super().__init__()
		self._counter = 0
		self._thread = None
		self._file = Path('/tmp/snipswatch.txt')
		self._thread = None

		self._importantColoring = re.compile('([\'"].+[\'"])')
		self._intentColoring = re.compile('detected intent ([a-zA-Z0-9:]+?)')
		self._timeColoring = re.compile('(\[[0-9]{2}:[0-9]{2}:[0-9]{2}\])')

		if self._file.exists():
			subprocess.run(['sudo', 'rm', self._file])


	def index(self):
		return render_template('snipswatch.html', langData=self._langData)


	def startWatching(self):
		process = subprocess.Popen('snips-watch -vv --no-color', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		conv = Ansi2HTMLConverter()

		flag = SuperManager.getInstance().threadManager.newLock('running')
		flag.set()
		while flag.isSet():
			out = process.stdout.readline().decode()
			if out != '':
				with self._file.open('a+') as fp:
					#line = commons.ansiToHtml(out)
					line = self._importantColoring.sub('<span class="logYellow">\\1</span>', line)
					line = self._intentColoring.sub('<span class="logYellow">\\1</span>', line)
					line = self._timeColoring.sub('<span class="logYellow">\\1</span>', line)
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
