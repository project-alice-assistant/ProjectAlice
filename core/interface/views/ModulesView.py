from flask import render_template

from core.base.SuperManager import SuperManager
from core.interface.views.View import View


class ModulesView(View):

	def __init__(self):
		super().__init__()

	def index(self):
		modules = {moduleName: module['instance'] for moduleName, module in SuperManager.getInstance().moduleManager.getModules(False).items()}
		deactivatedModules = {moduleName: module['instance'] for moduleName, module in SuperManager.getInstance().moduleManager.deactivatedModules.items()}
		modules = {**modules, **deactivatedModules}

		# TODO Remove for prod!!
		modules['DateDayTimeYear'].updateAvailable = True

		return render_template('modules.html', modules=modules, langData=self._langData)