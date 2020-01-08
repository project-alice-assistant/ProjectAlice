from flask import jsonify, request

from core.interface.model.Api import Api


class LoginApi(Api):
	route_base = f'/api/{Api.version()}/login/'


	def __init__(self):
		super().__init__()


	def post(self):
		try:
			username = request.form.get('username')
			if not self.UserManager.checkPinCode(self.UserManager.getUser(username), request.form.get('pin')):
				raise Exception

			token = self.UserManager.getUser(username).apiToken or self.UserManager.createApiToken(self.UserManager.getUser(username))

			return jsonify({'apiToken': token})
		except:
			return jsonify(message='ERROR: Unauthorized')
