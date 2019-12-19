from flask import render_template

from core.interface.model.View import View


class ScenarioView(View):
	route_base = '/scenarios/'

	def index(self):
		tiles = self.SkillManager.allScenarioTiles()
		return render_template(template_name_or_list='scenarios.html',
		                       langData=self._langData,
		                       tiles=tiles,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)
