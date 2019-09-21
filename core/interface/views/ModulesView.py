from flask_classful import FlaskView
from flask import render_template

from core.base.SuperManager import SuperManager


class ModulesView(FlaskView):

	def index(self):
		modules = {moduleName: module['instance'] for moduleName, module in SuperManager.getInstance().moduleManager.getModules(False).items()}
		deactivatedModules = {moduleName: module['instance'] for moduleName, module in SuperManager.getInstance().moduleManager.deactivatedModules.items()}
		modules = {**modules, **deactivatedModules}

		# TODO Remove for prod!!
		modules['DateDayTimeYear'].updateAvailable = True

		return render_template('modules.html', modules=modules)