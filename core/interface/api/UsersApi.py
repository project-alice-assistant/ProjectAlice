from flask import jsonify

from core.interface.model.Api import Api
from core.util.Decorators import ApiAuthenticated


class UsersApi(Api):
	route_base = f'/api/{Api.version()}/users/'


	def __init__(self):
		super().__init__()


	@ApiAuthenticated
	def index(self):
		return jsonify(data=[user.toJson() for user in self.UserManager.users.values()])


	@ApiAuthenticated
	def get(self, userId: int):
		return jsonify(data=self.UserManager.getUserById(userId).toJson())
