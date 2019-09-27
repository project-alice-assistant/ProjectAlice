from collections import OrderedDict

from flask import render_template, request, jsonify
from flask_classful import route

from core.base.SuperManager import SuperManager
from core.interface.views.View import View


class ModulesView(View):
	route_base = '/modules/'

	def __init__(self):
		super().__init__()
		self._on = "it's on baby"

	def index(self):
		modules = {moduleName: module['instance'] for moduleName, module in SuperManager.getInstance().moduleManager.getModules(False).items()}
		deactivatedModules = {moduleName: module['instance'] for moduleName, module in SuperManager.getInstance().moduleManager.deactivatedModules.items()}
		modules = {**modules, **deactivatedModules}
		modules = OrderedDict(sorted(modules.items()))

		# TODO Remove for prod!!
		modules['DateDayTimeYear'].updateAvailable = True

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
			self._logger.warning('[Modules] Failed toggling module: {}'.format(e))
			return self.index()