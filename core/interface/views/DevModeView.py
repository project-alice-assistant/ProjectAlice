from flask import jsonify, render_template, request

from core.interface.model.View import View


class DevModeView(View):
	route_base = '/devmode/'


	def __init__(self):
		super().__init__()


	def index(self):
		return render_template(template_name_or_list='devmode.html',
		                       langData=self._langData,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)


	def get(self, skillName: str):
		if self.SkillStoreManager.skillExists(skillName):
			return jsonify(success=False)
		else:
			return jsonify(success=True)


	def put(self, skillName: str):
		try:
			newSkill = {
				'name'                  : skillName,
				'description'           : request.form.get('description', 'Missing description'),
				'fr'                    : request.form.get('fr', False),
				'de'                    : request.form.get('de', False),
				'pipreq'                : request.form.get('pipreq', ''),
				'sysreq'                : request.form.get('sysreq', ''),
				'conditionOnline'       : request.form.get('sysreq', False),
				'conditionASRArbitrary' : request.form.get('conditionASRArbitrary', False),
				'conditionSkill'        : request.form.get('conditionSkill', ''),
				'conditionNotSkill'     : request.form.get('conditionNotSkill', ''),
				'conditionActiveManager': request.form.get('conditionActiveManager', '')
			}
			if not self.SkillManager.createNewSkill(newSkill):
				raise Exception('Unhandled skill creation exception')

			return jsonify(success=True)

		except Exception as e:
			self.logError(f'Something went wrong creating a new skill: {e}')
			return jsonify(success=False)
