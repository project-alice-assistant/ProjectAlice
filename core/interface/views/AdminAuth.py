from flask import render_template, request, jsonify

from core.interface.model.View import View


class AdminAuth(View):
	route_base = '/adminAuth/'

	def index(self):
		self.ModuleManager.getModuleInstance('AliceCore').explainInterfaceAuth()
		return render_template('adminAuth.html', langData=self._langData)


	def authenticate(self):
		try:
			code = request.form.get('usercode')
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed auth trial: {e}')
			return jsonify(success=False)
