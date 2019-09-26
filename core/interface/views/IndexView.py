import json

from flask import render_template, request, send_from_directory
from flask_classful import route

from core.base.SuperManager import SuperManager
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


	@route('widget_static/<path:filename>')
	def widget_static(self, filename: str):
		parent, fileType, filename = filename.split('/')
		return send_from_directory('{}/../../modules/{}/widgets/{}/'.format(
			SuperManager.getInstance().webInterfaceManager.app.root_path,
			parent,
			fileType
		), filename)


	@route('/home/saveWidgetPos', methods=['POST'])
	def saveWidgetPosition(self):
		try:
			p, w = request.form.get('id').split('_')

			widget = self.ModuleManager.widgets[p][w]
			widget.x = request.form.get('x')
			widget.y = request.form.get('y')
			widget.saveToDB()

			return json.dumps({'status': 'OK'})
		except Exception as e:
			self._logger.warning("[Widget] Couldn't save position: {}".format(e))
			return json.dumps({'status': 'FAILED'})


	@route('/home/removeWidget', methods=['POST'])
	def removeWidget(self):
		try:
			p, w = request.form.get('id').split('_')

			widget = self.ModuleManager.widgets[p][w]
			widget.state = 0
			widget.saveToDB()

			return json.dumps({'status': 'OK'})
		except Exception as e:
			self._logger.warning("[Widget] Couldn't remove from home: {}".format(e))
			return json.dumps({'status': 'FAILED'})


	@route('/home/addWidget', methods=['POST'])
	def addWidget(self):
		try:
			line, p, w = request.form.get('id').split('_')

			widget = self.ModuleManager.widgets[p][w]
			widget.state = 1
			widget.saveToDB()

			return json.dumps({'status': 'OK'})
		except Exception as e:
			self._logger.warning("[Widget] Couldn't add to home: {}".format(e))
			return json.dumps({'status': 'FAILED'})