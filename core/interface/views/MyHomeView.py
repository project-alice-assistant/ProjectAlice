import json
from pathlib import Path

from flask import jsonify, render_template, request

from core.interface.model.View import View


class MyHomeView(View):
	route_base = '/myhome/'

	def index(self):
		data = dict()
		file = Path(self.Commons.rootDir(), 'system/myHouse/myhouse.json')
		if file.exists():
			data = file.read_text()

		return render_template(template_name_or_list='myHome.html',
		                       langData=self._langData,
		                       houseData=data,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)



	def put(self):
		try:
			data = json.loads(request.form['data'])
			with Path(self.Commons.rootDir(), 'system/myHouse/myhouse.json').open('w') as fp:
				fp.write(json.dumps(data, indent=4))

			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed saving house map: {e}')
			return jsonify(success=False)
