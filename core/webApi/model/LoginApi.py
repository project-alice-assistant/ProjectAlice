from flask import jsonify, request
from flask_classful import route

from core.interface.model.Api import Api
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

			return jsonify(apiToken=token, authLevel=self.UserManager.getUser(username).accessLevel)
		except:
			return jsonify(message='ERROR: Unauthorized')


	@route('/checkToken/', methods=['POST'])
	@ApiAuthenticated
	def checkToken(self):
		try:
			return jsonify(success=True)
		except:
			return jsonify(message='ERROR: Unauthorized')
