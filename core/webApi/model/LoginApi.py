from flask import jsonify, request
from flask_classful import route

from core.webApi.model.Api import Api
from core.util.Decorators import ApiAuthenticated


class LoginApi(Api):
	route_base = f'/api/{Api.version()}/login/'


	def __init__(self):
		super().__init__()


	@route('/', methods=['POST'])
	def login(self):
		try:
			username = request.form.get('username')
			if not self.UserManager.checkPinCode(self.UserManager.getUser(username), request.form.get('pin')):
				raise Exception

			token = self.UserManager.getUser(username).apiToken or self.UserManager.createApiToken(self.UserManager.getUser(username))

			return jsonify(apiToken=token, authLevel=self.UserManager.apiTokenLevel(token))
		except:
			return jsonify(message='ERROR: Unauthorized')


	@route('/checkToken/', methods=['POST'])
	@ApiAuthenticated
	def checkToken(self):
		try:
			return jsonify(success=True, authLevel=self.UserManager.apiTokenLevel(request.headers.get('auth')))
		except:
			return jsonify(message='ERROR: Unauthorized')
