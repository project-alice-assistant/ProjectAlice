from flask import render_template

from core.interface.model.View import View


class SyslogView(View):
	route_base = '/syslog/'


	def __init__(self):
		super().__init__()


	def index(self):
		return render_template(template_name_or_list='syslog.html',
		                       langData=self._langData,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)
