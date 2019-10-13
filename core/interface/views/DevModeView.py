from flask import render_template

from core.interface.views.View import View


class DevModeView(View):
	route_base = '/devmode/'

	def __init__(self):
		super().__init__()


	def index(self):
		return render_template('devmode.html', langData=self._langData, devMode=self.ConfigManager.getAliceConfigByName('webInterfaceDevMode'))