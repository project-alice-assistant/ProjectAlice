from flask import jsonify, request
from flask_classful import route

from core.interface.model.Api import Api


class ModulesApi(Api):

	route_base = f'/api/{Api.version()}/modules/'

	def __init__(self):
		super().__init__()


	def index(self):
		return jsonify(data=[module.toJson() for module in self.ModuleManager.allModules.values()])


	def delete(self, moduleName: str):
		if moduleName in self.ModuleManager.neededModules:
			return jsonify(success=False, reason='module cannot be deleted')

		try:
			self.ModuleManager.removeModule(moduleName)
			return jsonify(success=True)
		except Exception as e:
			return jsonify(success=False, reason=f'Failed deleting module: {e}')


	def get(self, moduleName: str):
		module = self.ModuleManager.getModuleInstance(moduleName=moduleName, silent=True)
		module = module.toJson() if module else dict()

		return jsonify(data=module)


	@route('/<moduleName>/toggleActiveState/')
	def toggleActiveState(self, moduleName: str):
		if moduleName not in self.ModuleManager.allModules:
			return jsonify(success=False, reason='module not found')

		if self.ModuleManager.isModuleActive(moduleName):
			if moduleName in self.ModuleManager.neededModules:
				return jsonify(success=False, reason='module cannot be deactivated')

			self.ModuleManager.deactivateModule(moduleName=moduleName, persistent=True)
		else:
			self.ModuleManager.activateModule(moduleName=moduleName, persistent=True)

		return jsonify(success=True)


	@route('/<moduleName>/activate/', methods=['GET', 'POST'])
	def activate(self, moduleName: str):
		if moduleName not in self.ModuleManager.allModules:
			return jsonify(success=False, reason='module not found')

		if self.ModuleManager.isModuleActive(moduleName):
			return jsonify(success=False, reason='already active')
		else:
			persistent = request.form.get('persistent') is not None and request.form.get('persistent') == 'true'
			self.ModuleManager.activateModule(moduleName=moduleName, persistent=persistent)
			return jsonify(success=True)


	@route('/<moduleName>/deactivate/', methods=['GET', 'POST'])
	def deactivate(self, moduleName: str):
		if moduleName not in self.ModuleManager.allModules:
			return jsonify(success=False, reason='module not found')

		if moduleName in self.ModuleManager.neededModules:
			return jsonify(success=False, reason='module cannot be deactivated')

		if self.ModuleManager.isModuleActive(moduleName):
			persistent = request.form.get('persistent') is not None and request.form.get('persistent') == 'true'
			self.ModuleManager.deactivateModule(moduleName=moduleName, persistent=persistent)
			return jsonify(success=True)
		else:
			return jsonify(success=False, reason='not active')


	@route('/<moduleName>/checkUpdate/')
	def checkUpdate(self, moduleName: str):
		if moduleName not in self.ModuleManager.allModules:
			return jsonify(success=False, reason='module not found')

		return jsonify(success=self.ModuleManager.checkForModuleUpdates(moduleToCheck=moduleName))
