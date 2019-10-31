import subprocess

from flask import render_template, request, jsonify

from core.interface.model.View import View


class ModulesView(View):
	route_base = '/modules/'


	def index(self):
		modules = {**self.ModuleManager.getModules(False), **self.ModuleManager.deactivatedModules}
		modules = {moduleName: module['instance'] for moduleName, module in sorted(modules.items())}

		return render_template(template_name_or_list='modules.html',
		                       modules=modules,
		                       langData=self._langData,
		                       devMode=self.ConfigManager.getAliceConfigByName('webInterfaceDevMode'),
		                       updateChannel=self.ConfigManager.getAliceConfigByName('updateChannel'))


	def toggleModule(self):
		try:
			_, module = request.form.get('id').split('_')
			if self.ModuleManager.isModuleActive(module):
				self.ModuleManager.deactivateModule(moduleName=module, persistent=True)
			else:
				self.ModuleManager.activateModule(moduleName=module, persistent=True)

			return self.index()
		except Exception as e:
			self.logWarning(f'Failed toggling module: {e}', printStack=True)
			return self.index()


	def deleteModule(self):
		try:
			_, module = request.form.get('id').split('_')
			self.ModuleManager.removeModule(module)
			return self.index()
		except Exception as e:
			self.logWarning(f'Failed deleting module: {e}', printStack=True)
			return self.index()


	def saveModuleSettings(self):
		moduleName = request.form['moduleName']
		for confName, confValue in request.form.items():
			if confName == 'moduleName':
				continue

			if confValue == 'on':
				confValue = True
			elif confValue == 'off':
				confValue = False

			self.ConfigManager.updateModuleConfigurationFile(
				moduleName=moduleName,
				key=confName,
				value=confValue
			)

		return self.index()


	def installModule(self):
		try:
			module = request.form.get('module')
			self.WebInterfaceManager.newModuleInstallProcess(module)
			subprocess.run(['wget', f'http://modules.projectalice.ch/{module}', '-O', f'{module}.install'])
			subprocess.run(['mv', f'{module}.install', f'{self.Commons.rootDir()}/system/moduleInstallTickets/{module}.install'])
			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f'Failed installing module: {e}', printStack=True)
			return jsonify(success=False)


	def checkInstallStatus(self):
		module = request.form.get('module')
		status = self.WebInterfaceManager.moduleInstallProcesses.get(module, {'status': 'unknown'})['status']
		return jsonify(status)
