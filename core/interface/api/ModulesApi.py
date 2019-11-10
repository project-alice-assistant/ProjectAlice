from flask import jsonify

from core.interface.model.Api import Api


class UsersApi(Api):

	route_base = f'/api/{Api.version()}/modules/'

	def __init__(self):
		super().__init__()


	def index(self):
		return jsonify(data=[user.toJson() for user in self.UserManager.users.values()])


	def get(self, module: str):
		return jsonify(data=self.UserManager.getUserById(userId).toJson())
