from flask import render_template, request
from flask_classful import route

from core.interface.views.View import View


class AdminView(View):
	route_base = '/admin/'

	def __init__(self):
		super().__init__()


	def index(self):
		return render_template('admin.html',
		                       langData=self._langData,
		                       devMode=self.ConfigManager.getAliceConfigByName('webInterfaceDevMode'),
		                       updateChannel=self.ConfigManager.getAliceConfigByName('updateChannel'),
		                       aliceSettings=self.ConfigManager.aliceConfigurations)


	@route('/saveAliceSettings', methods=['POST'])
	def saveAliceSettings(self):
		try:
			confs = {key: False if value == 'off' else True if value == 'on' else value for key, value in request.form.items()}

			confs['modules'] = self.ConfigManager.getAliceConfigByName('modules')
			confs['supportedLanguages'] = self.ConfigManager.getAliceConfigByName('supportedLanguages')

			self.ConfigManager.writeToAliceConfigurationFile(confs=confs)
			return self.index()
		except Exception as e:
			self.logError(f'Failed saving Alice config: {e}')
			return self.index()
