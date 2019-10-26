from pathlib import Path

import tempfile

from flask import jsonify, render_template, request

from core.interface.model.View import View


class SnipswatchView(View):
	route_base = '/snipswatch/'


	def __init__(self):
		super().__init__()
		self._counter = 0
		self._thread = None
		self._file = Path(tempfile.gettempdir(), 'snipswatch')
		self._process = None


	def index(self):
		self.SnipsWatchManager.startWatching()
		return render_template('snipswatch.html',
		                       langData=self._langData,
		                       devMode=self.ConfigManager.getAliceConfigByName('webInterfaceDevMode'),
		                       updateChannel=self.ConfigManager.getAliceConfigByName('updateChannel'))


	def refreshConsole(self):
		return jsonify(data=self.SnipsWatchManager.getLogs())


	def verbosity(self):
		try:
			if self._process:
				self._process.terminate()

			verbosity = int(request.form.get('verbosity'))
			self.SnipsWatchManager.setVerbosity(verbosity)
			return self.refreshConsole()
		except Exception as e:
			self.logError(f'Error setting verbosity: {e}')
			return jsonify(success=False)



