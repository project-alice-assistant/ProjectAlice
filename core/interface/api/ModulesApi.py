from flask import jsonify, request
from flask_classful import route

from core.interface.model.Api import Api


class ModulesApi(Api):

	route_base = f'/api/{Api.version()}/modules/'

	def __init__(self):
		super().__init__()


	def index(self):
		return jsonify(data=[module.toJson() for module in self.SkillManager.allModules.values()])


	def delete(self, skillName: str):
		if skillName in self.SkillManager.neededModules:
			return jsonify(success=False, reason='module cannot be deleted')

		try:
			self.SkillManager.removeModule(skillName)
			return jsonify(success=True)
		except Exception as e:
			return jsonify(success=False, reason=f'Failed deleting module: {e}')


	def get(self, skillName: str):
		module = self.SkillManager.getSkillInstance(skillName=skillName, silent=True)
		module = module.toJson() if module else dict()

		return jsonify(data=module)


	@route('/<skillName>/toggleActiveState/')
	def toggleActiveState(self, skillName: str):
		if skillName not in self.SkillManager.allModules:
			return jsonify(success=False, reason='module not found')

		if self.SkillManager.isModuleActive(skillName):
			if skillName in self.SkillManager.neededModules:
				return jsonify(success=False, reason='module cannot be deactivated')

			self.SkillManager.deactivateSkill(skillName=skillName, persistent=True)
		else:
			self.SkillManager.activateModule(skillName=skillName, persistent=True)

		return jsonify(success=True)


	@route('/<skillName>/activate/', methods=['GET', 'POST'])
	def activate(self, skillName: str):
		if skillName not in self.SkillManager.allModules:
			return jsonify(success=False, reason='module not found')

		if self.SkillManager.isModuleActive(skillName):
			return jsonify(success=False, reason='already active')
		else:
			persistent = request.form.get('persistent') is not None and request.form.get('persistent') == 'true'
			self.SkillManager.activateModule(skillName=skillName, persistent=persistent)
			return jsonify(success=True)


	@route('/<skillName>/deactivate/', methods=['GET', 'POST'])
	def deactivate(self, skillName: str):
		if skillName not in self.SkillManager.allModules:
			return jsonify(success=False, reason='module not found')

		if skillName in self.SkillManager.neededModules:
			return jsonify(success=False, reason='module cannot be deactivated')

		if self.SkillManager.isModuleActive(skillName):
			persistent = request.form.get('persistent') is not None and request.form.get('persistent') == 'true'
			self.SkillManager.deactivateSkill(skillName=skillName, persistent=persistent)
			return jsonify(success=True)
		else:
			return jsonify(success=False, reason='not active')


	@route('/<skillName>/checkUpdate/')
	def checkUpdate(self, skillName: str):
		if skillName not in self.SkillManager.allModules:
			return jsonify(success=False, reason='module not found')

		return jsonify(success=self.SkillManager.checkForModuleUpdates(moduleToCheck=skillName))
