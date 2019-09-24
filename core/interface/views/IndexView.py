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
		return render_template('home.html', widgets=self.WebInterfaceManager.widgets, langData=self._langData)


	@route('/home/saveWidgetPos', methods=['POST'])
	def saveWidgetPosition(self):
		try:
			x = request.form.get('x')
			y = request.form.get('y')
			return json.dumps({'status': 'OK'})
		except:
			return json.dumps({'status': 'FAILED'})