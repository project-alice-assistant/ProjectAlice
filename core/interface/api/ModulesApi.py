from flask import jsonify, request
from flask_classful import route

from core.interface.model.Api import Api


class ModulesApi(Api):

	route_base = f'/api/{Api.version()}/modules/'

	def __init__(self):
		super().__init__()


	def index(self):
		return jsonify(data=[module.toJson() for module in self.ModuleManager.allModules.values()])


	def delete(self, skillName: str):
		if skillName in self.ModuleManager.neededModules:
			return jsonify(success=False, reason='module cannot be deleted')

		try:
			self.ModuleManager.removeModule(skillName)
			return jsonify(success=True)
		except Exception as e:
			return jsonify(success=False, reason=f'Failed deleting module: {e}')


	def get(self, skillName: str):
		module = self.ModuleManager.getModuleInstance(skillName=skillName, silent=True)
		module = module.toJson() if module else dict()

		return jsonify(data=module)


	@route('/<skillName>/toggleActiveState/')
	def toggleActiveState(self, skillName: str):
		if skillName not in self.ModuleManager.allModules:
			return jsonify(success=False, reason='module not found')

		if self.ModuleManager.isModuleActive(skillName):
			if skillName in self.ModuleManager.neededModules:
				return jsonify(success=False, reason='module cannot be deactivated')

			self.ModuleManager.deactivateModule(skillName=skillName, persistent=True)
		else:
			self.ModuleManager.activateModule(skillName=skillName, persistent=True)

		return jsonify(success=True)


	@route('/<skillName>/activate/', methods=['GET', 'POST'])
	def activate(self, skillName: str):
		if skillName not in self.ModuleManager.allModules:
			return jsonify(success=False, reason='module not found')

		if self.ModuleManager.isModuleActive(skillName):
			return jsonify(success=False, reason='already active')
		else:
			persistent = request.form.get('persistent') is not None and request.form.get('persistent') == 'true'
			self.ModuleManager.activateModule(skillName=skillName, persistent=persistent)
			return jsonify(success=True)


	@route('/<skillName>/deactivate/', methods=['GET', 'POST'])
	def deactivate(self, skillName: str):
		if skillName not in self.ModuleManager.allModules:
			return jsonify(success=False, reason='module not found')

		if skillName in self.ModuleManager.neededModules:
			return jsonify(success=False, reason='module cannot be deactivated')

		if self.ModuleManager.isModuleActive(skillName):
			persistent = request.form.get('persistent') is not None and request.form.get('persistent') == 'true'
			self.ModuleManager.deactivateModule(skillName=skillName, persistent=persistent)
			return jsonify(success=True)
		else:
			return jsonify(success=False, reason='not active')


	@route('/<skillName>/checkUpdate/')
	def checkUpdate(self, skillName: str):
		if skillName not in self.ModuleManager.allModules:
			return jsonify(success=False, reason='module not found')

		return jsonify(success=self.ModuleManager.checkForModuleUpdates(moduleToCheck=skillName))
