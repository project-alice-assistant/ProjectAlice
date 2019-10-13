from flask import render_template

from core.interface.views.View import View


class AdminView(View):

	def __init__(self):
		super().__init__()


	def index(self):
		return render_template('admin.html', langData=self._langData, devMode=self.ConfigManager.getAliceConfigByName('webInterfaceDevMode'))