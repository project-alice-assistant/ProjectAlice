import subprocess
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

		return render_template(template_name_or_list='modules.html',
		                       modules=modules,
		                       langData=self._langData,
		                       devMode=self.ConfigManager.getAliceConfigByName('webInterfaceDevMode'),
		                       updateChannel=self.ConfigManager.getAliceConfigByName('updateChannel'))


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
			self.logWarning(f'Failed toggling module: {e}')
			return self.index()


	@route('/delete', methods=['POST'])
	def deleteModule(self):
		try:
			action, module = request.form.get('id').split('_')
			self.ModuleManager.removeModule(module)
			return self.index()
		except Exception as e:
			self.logWarning(f'Failed deleting module: {e}')
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


	@route('/install', methods=['POST'])
	def installModule(self):
		try:
			module = request.form.get('module')
			self.WebInterfaceManager.newModuleInstallProcess(module)
			subprocess.run(['wget', f'http://modules.projectalice.ch/{module}', '-O', f'{module}.install'])
			subprocess.run(['mv', f'{module}.install', f'{self.Commons.rootDir()}/system/moduleInstallTickets/{module}.install'])
			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f'Failed installing module: {e}')
			return jsonify(success=False)


	@route('/checkInstallStatus', methods=['POST'])
	def checkInstallStatus(self):
		module = request.form.get('module')
		status = self.WebInterfaceManager.moduleInstallProcesses.get(module, {'status': 'unknown'})['status']
		return jsonify(status)
