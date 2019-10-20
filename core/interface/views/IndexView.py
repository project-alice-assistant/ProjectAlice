from flask import render_template, request, send_from_directory, jsonify, redirect
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
		return render_template('home.html',
		                       widgets=self.ModuleManager.widgets,
		                       langData=self._langData,
		                       devMode=self.ConfigManager.getAliceConfigByName('webInterfaceDevMode'),
		                       updateChannel=self.ConfigManager.getAliceConfigByName('updateChannel'))


	@route('widget_static/<path:filename>')
	def widget_static(self, filename: str):
		parent, fileType, filename = filename.split('/')
		return send_from_directory(
			f'{self.WebInterfaceManager.app.root_path}/../../modules/{parent}/widgets/{fileType}/', filename)


	@route('/home/saveWidgetPos', methods=['POST'])
	def saveWidgetPosition(self):
		try:
			data = request.get_json()
			p, w = data['id'].split('_')

			widget = self.ModuleManager.widgets[p][w]
			widget.x = data['x']
			widget.y = data['y']
			widget.saveToDB()

			order = data['order']
			for index, widget in enumerate(order, start=1):
				widgetParent, widgetName = widget.split('_')
				widget = self.ModuleManager.widgets[widgetParent][widgetName]
				widget.zindex = index
				widget.saveToDB()

			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f"[Widget] Couldn't save position: {e}")
			return jsonify(success=False)


	@route('/home/removeWidget', methods=['POST'])
	def removeWidget(self):
		try:
			p, w = request.form.get('id').split('_')

			widget = self.ModuleManager.widgets[p][w]
			widget.state = 0
			widget.saveToDB()

			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f"[Widget] Couldn't remove from home: {e}")
			return jsonify(success=False)


	@route('/home/addWidget', methods=['POST'])
	def addWidget(self):
		try:
			line, p, w = request.form.get('id').split('_')

			widget = self.ModuleManager.widgets[p][w]
			widget.state = 1
			widget.saveToDB()

			return redirect('home.html')
		except Exception as e:
			self.logWarning(f"[Widget] Couldn't add to home: {e}")
			return jsonify(success=False)
