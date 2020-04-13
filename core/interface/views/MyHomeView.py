from flask import render_template

from core.interface.model.View import View


class MyHomeView(View):
	route_base = '/myhome/'

	def index(self):
		return render_template(template_name_or_list='myHome.html',
		                       langData=self._langData,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)
