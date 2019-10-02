from collections import OrderedDict

from flask import render_template, request, jsonify
from flask_classful import route

from core.base.SuperManager import SuperManager
from core.interface.views.View import View


class ModulesView(View):
	route_base = '/modules/'

	def __init__(self):
		super().__init__()


	def index(self):
		modules = {moduleName: module['instance'] for moduleName, module in SuperManager.getInstance().moduleManager.getModules(False).items()}
		deactivatedModules = {moduleName: module['instance'] for moduleName, module in SuperManager.getInstance().moduleManager.deactivatedModules.items()}
		modules = {**modules, **deactivatedModules}
		modules = OrderedDict(sorted(modules.items()))

		return render_template('modules.html', modules=modules, langData=self._langData)


	@route('/toggle', methods=['POST'])
	def toggleModule(self):
		try:
			action, module = request.form.get('id').split('_')
			if self.ModuleManager.isModuleActive(module):
				self.ModuleManager.deactivateModule(moduleName=module, persistent=True)
			else:
				self.ModuleManager.activateModule(moduleName=module, persistent=True)

			return self.index()
		except Exception as e:
			self._logger.warning(f'[Modules] Failed toggling module: {e}')
			return self.index()


	@route('/delete', methods=['POST'])
	def toggleModule(self):
		try:
			action, module = request.form.get('id').split('_')
			self.ModuleManager.removeModule(module)
			return self.index()
		except Exception as e:
			self._logger.warning(f'[Modules] Failed deleting module: {e}')
			return self.index()


	@route('/saveModuleSettings', methods=['POST'])
	def saveModuleSettings(self):
		moduleName = request.form['moduleName']
		for confName, confValue in request.form.items():
			if confName == 'moduleName':
				continue

			if confValue == 'on':
				confValue = True
			elif confValue == 'off':
				confValue = False

			SuperManager.getInstance().configManager.updateModuleConfigurationFile(
				moduleName=moduleName,
				key=confName,
				value=confValue
			)

		return self.index()