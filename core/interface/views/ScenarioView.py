from flask import render_template

from core.interface.model.View import View


class ScenarioView(View):
	route_base = '/scenarios/'

	def index(self):
		return render_template(template_name_or_list='scenarios.html',
		                       myIp=self.Commons.getLocalIp(),
		                       **self._everyPagesRenderValues)
