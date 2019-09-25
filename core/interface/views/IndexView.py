import json

from flask import render_template, request
from flask_classful import route

from core.interface.views.View import View


class IndexView(View):
	route_base = '/'

	def __init__(self):
		super().__init__()


	@route('/', endpoint='index')
	@route('/home/', endpoint='index')
	@route('/index/', endpoint='index')
	def index(self):
		return render_template('home.html', widgets=self.ModuleManager.widgets, langData=self._langData)


	@route('/home/saveWidgetPos', methods=['POST'])
	def saveWidgetPosition(self):
		try:
			p, w = request.form.get('id').split('_')

			widget = self.ModuleManager.widgets[p][w]
			widget.x = request.form.get('x')
			widget.y = request.form.get('y')
			widget.saveToDB()

			return json.dumps({'status': 'OK'})
		except:
			return json.dumps({'status': 'FAILED'})