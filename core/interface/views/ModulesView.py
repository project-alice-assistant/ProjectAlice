from flask_classful import FlaskView
from flask import render_template

from core.base.SuperManager import SuperManager


class ModulesView(FlaskView):

	def index(self):
		return render_template('modules.html', modules=SuperManager.getInstance().moduleManager.getModules(False))