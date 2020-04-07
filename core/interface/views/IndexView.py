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


	@route('/home/saveWidgetPosition/', methods=['POST'])
	def saveWidgetPosition(self):
		try:
			p, w = request.form['id'].split('_')

			widget = self.SkillManager.widgets[p][w]
			widget.x = request.form['x']
			widget.y = request.form['y']
			widget.saveToDB()

			order = json.loads(request.form['order'])
			for index, widget in enumerate(order, start=1):
				widgetParent, widgetName = widget.split('_')
				widget = self.SkillManager.widgets[widgetParent][widgetName]
				widget.zindex = index
				widget.saveToDB()

			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f"[Widget] Couldn't save position: {e}")
			return jsonify(success=False)


	@route('/home/saveWidgetSize/', methods=['POST'])
	def saveWidgetSize(self):
		try:
			self.logInfo(request)
			p, w = request.form['id'].split('_')

			widget = self.SkillManager.widgets[p][w]
			widget.width = int(request.form['w'])
			widget.height = int(request.form['h'])
			widget.saveToDB()

			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f"[Widget] Couldn't save size: {e}")
			return jsonify(success=False)


	@route('/home/removeWidget/', methods=['POST'])
	def removeWidget(self):
		try:
			p, w = request.form.get('id').split('_')

			widget = self.SkillManager.widgets[p][w]
			widget.state = 0
			widget.saveToDB()

			return jsonify(success=True)
		except Exception as e:
			self.logWarning(f"[Widget] Couldn't remove from home: {e}")
			return jsonify(success=False)


	@route('/home/addWidget/', methods=['POST'])
	def addWidget(self):
		try:
			line, p, w = request.form.get('id').split('_')

			widget = self.SkillManager.widgets[p][w]
			widget.state = 1
			widget.saveToDB()

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
			return func(**json.loads(data['param']))
		except Exception as e:
			self.logWarning(f"[Widget] Widget tried to call a core function but failed: {e}")
			return jsonify(success=False)


	@route('/home/saveWidgetConfig/', methods=['POST'])
	def saveWidgetConfig(self):
		p, w = request.form.get('id').split('_')
		skill = self.SkillManager.getSkillInstance(skillName=p)
		widget = skill.getWidgetInstance(w)
		widget.options.update(request.form)
		# 'id' would mess up the complete form anyways, must not be used!
		widget.options.pop('id', None)
		widget.saveToDB()
		return jsonify(success=True)


	@route('/home/readWidgetConfig/', methods=['POST'])
	def readWidgetConfig(self):
		p, w = request.form.get('id').split('_')
		skill = self.SkillManager.getSkillInstance(skillName=p)
		widget = skill.getWidgetInstance(w)
		return jsonify(widget.options)


	@route('/home/saveWidgetCustStyle/', methods=['POST'])
	def saveWidgetCustStyle(self):
		p, w = request.form.get('id').split('_')
		skill = self.SkillManager.getSkillInstance(skillName=p)
		widget = skill.getWidgetInstance(w)
		widget.custStyle.update(request.form)
		# 'id' would mess up the complete form anyways, must not be used!
		widget.custStyle.pop('id', None)
		widget.saveToDB()
		return jsonify(success=True)


	@route('/home/readWidgetCustStyle/', methods=['POST'])
	def readWidgetCustStyle(self):
		p, w = request.form.get('id').split('_')
		skill = self.SkillManager.getSkillInstance(skillName=p)
		widget = skill.getWidgetInstance(w)
		return jsonify(widget.custStyle)


	@route('/home/getMqttConfig/', methods=['POST'])
	def getMqttConfig(self):
		return jsonify(
			success=True,
			host=self.ConfigManager.getAliceConfigByName('mqttHost'),
			port=int(self.ConfigManager.getAliceConfigByName('mqttPort')) + 1
		)
