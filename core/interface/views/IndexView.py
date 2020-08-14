import json

from flask import jsonify, redirect, render_template, request, send_from_directory
from flask_classful import route

from core.interface.model.View import View


class IndexView(View):
	route_base = '/'

	@route('/', endpoint='index')
	@route('/home/', endpoint='index')
	@route('/index/', endpoint='index')
	def index(self):
		return render_template(template_name_or_list='home.html',
		                       widgets=self.SkillManager.widgets,
		                       langData=self._langData,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)


	@route('widget_static/<path:filename>')
	def widget_static(self, filename: str):
		parent, fileType, filename = filename.split('/')
		return send_from_directory(f'{self.WebInterfaceManager.app.root_path}/../../skills/{parent}/widgets/{fileType}/', filename)


	@route('/home/saveWidgets/', methods=['POST'])
	def saveWidgets(self):
		try:
			data = request.json

			for identifier, widgetData in data.items():
				parent, widgetName = identifier.split('_')

				widget = self.SkillManager.widgets[parent][widgetName]
				widget.x = widgetData['x']
				widget.y = widgetData['y']
				widget.zindex = widgetData['zindex']
				widget.width = int(widgetData['w'])
				widget.height = int(widgetData['h'])
				widget.saveToDB()

			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f"[Widget] Couldn't save widget: {e}")
			return jsonify(success=False)


	@route('/home/removeWidget/', methods=['POST'])
	def removeWidget(self):
		try:
			parent, widgetName = request.form.get('id').split('_')

			widget = self.SkillManager.widgets[parent][widgetName]
			widget.state = 0
			widget.saveToDB()
			self.SkillManager.sortWidgetZIndexes()

			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f"[Widget] Couldn't remove from home: {e}")
			return jsonify(success=False)


	@route('/home/addWidget/', methods=['POST'])
	def addWidget(self):
		try:
			line, parent, widgetName = request.form.get('id').split('_')

			widget = self.SkillManager.widgets[parent][widgetName]
			widget.state = 1
			widget.saveToDB()
			self.SkillManager.sortWidgetZIndexes()

			return redirect('home.html')
		except Exception as e:
			self.logWarning(f"[Widget] Couldn't add to home: {e}")
			return jsonify(success=False)


	@route('/home/widget/', methods=['POST'])
	def widgetCall(self):
		try:
			data = request.json

			if not data['param']:
				data['param'] = '{}'

			skill = self.SkillManager.getSkillInstance(skillName=data['skill'])
			widget = skill.getWidgetInstance(data['widget'])
			func = getattr(widget, data['func'])
			ret = func(**json.loads(data['param']))
			if not ret:
				return jsonify(success=True)
			return ret
		except Exception as e:
			self.logWarning(f"[Widget] Widget tried to call a core function but failed: {e}")
			return jsonify(success=False)


	@route('/home/saveWidgetConfig/', methods=['POST'])
	def saveWidgetConfig(self):
		parent, widgetName = request.form.get('id').split('_')
		widget = self.SkillManager.widgets[parent][widgetName]
		widget.options.update(request.form)
		# 'id' would mess up the complete form anyways, must not be used!
		widget.options.pop('id', None)
		widget.saveToDB()
		return jsonify(success=True)


	@route('/home/readWidgetConfig/', methods=['POST'])
	def readWidgetConfig(self):
		parent, widgetName = request.form.get('id').split('_')
		widget = self.SkillManager.widgets[parent][widgetName]
		return jsonify(widget.options)


	@route('/home/saveWidgetCustStyle/', methods=['POST'])
	def saveWidgetCustStyle(self):
		parent, widgetName = request.form.get('id').split('_')
		widget = self.SkillManager.widgets[parent][widgetName]
		widget.custStyle.update(request.form)
		# 'id' would mess up the complete form anyways, must not be used!
		widget.custStyle.pop('id', None)
		widget.saveToDB()
		return jsonify(success=True)


	@route('/home/readWidgetCustStyle/', methods=['POST'])
	def readWidgetCustStyle(self):
		parent, widegetName = request.form.get('id').split('_')
		widget = self.SkillManager.widgets[parent][widegetName]
		return jsonify(widget.custStyle)


	@route('/home/getMqttConfig/', methods=['POST'])
	def getMqttConfig(self):
		return jsonify(
			success=True,
			host=self.ConfigManager.getAliceConfigByName('mqttHost'),
			port=int(self.ConfigManager.getAliceConfigByName('mqttPort')) + 1
		)
