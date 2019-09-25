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
			widget = self.WebInterfaceManager.widgets[request.form.get('id')]
			widget.x = request.form.get('x')
			widget.y = request.form.get('y')

			print(widget)

			query = 'UPDATE :__table__ SET posx = :posx, posy = :posy WHERE parent = :parent AND name = :name'
			values = {
				'parent': widget.parent,
				'name': widget.name,
				'posx': widget.x,
				'posy': widget.y
			}

			if self.DatabaseManager.update('widgets', self.WebInterfaceManager.name, values, query):
				return json.dumps({'status': 'OK'})
			else:
				raise Exception
		except:
			return json.dumps({'status': 'FAILED'})