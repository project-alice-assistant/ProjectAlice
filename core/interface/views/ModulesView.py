import subprocess

from flask import render_template, request, jsonify
import requests

from core.base.model.GithubCloner import GithubCloner
from core.base.model.Version import Version
from core.commons import constants
from core.interface.model.View import View


class ModulesView(View):
	route_base = '/modules/'


	def index(self):
		modules = {**self.ModuleManager.getModules(False), **self.ModuleManager.deactivatedModules}
		modules = {moduleName: module['instance'] for moduleName, module in sorted(modules.items())}

		return render_template(template_name_or_list='modules.html',
		                       modules=modules,
		                       langData=self._langData,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)


	def toggleModule(self):
		try:
			_, module = request.form.get('id').split('_')
			if self.ModuleManager.isModuleActive(module):
				self.ModuleManager.deactivateModule(moduleName=module, persistent=True)
			else:
				self.ModuleManager.activateModule(moduleName=module, persistent=True)
		except Exception as e:
			self.logWarning(f'Failed toggling module: {e}', printStack=True)
		
		return self.index()


	def deleteModule(self):
		try:
			_, module = request.form.get('id').split('_')
			self.ModuleManager.removeModule(module)
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


	def loadStoreData(self):
		installers = dict()
		updateSource = self.ConfigManager.getModulesUpdateSource()
		req = requests.get(
			url='https://api.github.com/search/code?q=extension:install+repo:project-alice-powered-by-snips/ProjectAliceModules/',
			auth=GithubCloner.getGithubAuth())
		results = req.json()
		if results:
			for module in results['items']:
				try:
					req = requests.get(
						url=module['url'].split('?')[0],
						params={'ref': updateSource},
						headers={'Accept': 'application/vnd.github.VERSION.raw'},
						auth=GithubCloner.getGithubAuth()
					)
					installer = req.json()
					if installer:
						installers[installer['name']] = installer
				except Exception:
					continue

		return {
			moduleName: moduleInfo for moduleName, moduleInfo in installers.items()
			if self.ModuleManager.getModuleInstance(moduleName=moduleName, silent=True) is None and Version(constants.VERSION) >= Version(moduleInfo['aliceMinVersion'])
		}
