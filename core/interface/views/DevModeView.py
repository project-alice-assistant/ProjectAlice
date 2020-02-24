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


	def uploadToGithub(self):
		try:
			skillName = request.form.get('skillName', '')
			skillDesc = request.form.get('skillDesc', '')

			if not skillName:
				raise Exception

			if self.SkillManager.uploadSkillToGithub(skillName, skillDesc):
				return jsonify(success=True, url=f'https://github.com/{self.ConfigManager.getAliceConfigByName("githubUsername")}/{skillName}.git')

			return jsonify(success=False)
		except Exception as e:
			self.logError(f'Failed uploading to github: {e}')
			return jsonify(success=False)


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
				'pipreq'                : request.form.get('pipreq', list()),
				'sysreq'                : request.form.get('sysreq', list()),
				'conditionOnline'       : request.form.get('sysreq', False),
				'conditionASRArbitrary' : request.form.get('conditionASRArbitrary', False),
				'conditionSkill'        : request.form.get('conditionSkill', list()),
				'conditionNotSkill'     : request.form.get('conditionNotSkill', list()),
				'conditionActiveManager': request.form.get('conditionActiveManager', list()),
				'widgets'               : request.form.get('widgets', list())
			}
			if not self.SkillManager.createNewSkill(newSkill):
				raise Exception('Unhandled skill creation exception')

			return jsonify(success=True)

		except Exception as e:
			self.logError(f'Something went wrong creating a new skill: {e}')
			return jsonify(success=False)
