from flask import render_template

from core.interface.model.View import View


class ScenariosView(View):
	route_base = '/scenarios/'
	counter = 0


	def index(self):
		return render_template(template_name_or_list='scenarios.html',
		                       langData=self._langData,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)
