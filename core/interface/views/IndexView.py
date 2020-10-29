import json

from flask import jsonify, render_template, request, send_from_directory
from flask_classful import route

from core.interface.model.View import View


class IndexView(View):
	route_base = '/'

	@route('/', endpoint='index')
	@route('/home/', endpoint='index')
	@route('/index/', endpoint='index')
	def index(self):
		super().index()
		return render_template(template_name_or_list='home.html',
		                       widgets=self.SkillManager.availableWidgets,
		                       **self._everyPagesRenderValues)


	@route('widget_static/<path:filename>')
	def widget_static(self, filename: str):
		parent, fileType, filename = filename.split('/')
		return send_from_directory(f'{self.WebInterfaceManager.app.root_path}/../../skills/{parent}/widgets/{fileType}/', filename)


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
			return jsonify(success=False, message=str(e))


	@route('/home/getMqttConfig/', methods=['POST'])
	def getMqttConfig(self):
		return jsonify(
			success=True,
			host=self.ConfigManager.getAliceConfigByName('mqttHost'),
			port=int(self.ConfigManager.getAliceConfigByName('mqttPort')) + 1
		)
