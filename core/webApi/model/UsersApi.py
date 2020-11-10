from flask import jsonify, request

from core.interface.model.Api import Api
from core.user.model.AccessLevels import AccessLevel
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


	@ApiAuthenticated
	def put(self):
		try:
			username = request.form.get('username', '').lower()
			pin = int(request.form.get('pin'))
			access = request.form.get('access')

			if not username or not pin or not access:
				return jsonify(message='ERROR: Make sure to specify username, pin and access level (admin, default, kid, worker, guest)')

			if self.UserManager.getUser(username):
				return jsonify(message=f"ERROR: User '{username}' is already existing")

			if not self.UserManager.hasAccessLevel(self.UserManager.getUserByAPIToken(request.headers.get('auth')).name, AccessLevel[access.upper()].value):
				return jsonify(message='ERROR: You cannot create a user with a higher access level than yours')

			self.UserManager.addNewUser(name=username, access=access, pinCode=pin)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed adding new user: {e}')
			return jsonify(success=False)


	@ApiAuthenticated
	def delete(self):
		try:
			if not self.UserManager.hasAccessLevel(self.UserManager.getUserByAPIToken(request.headers.get('auth')).name, AccessLevel.ADMIN):
				return jsonify(message='ERROR: You need admin access to delete a user')

			username = request.form.get('username', '').lower()
			keepWakeword = request.form.get('keepWakeword', False)
			keepWakeword = False if keepWakeword in {False, 'no', '0', 'false', 'False'} else True

			if not self.UserManager.getUser(username):
				return jsonify(message=f"ERROR: User '{username}' does not exist")

			self.UserManager.deleteUser(username=username, keepWakeword=keepWakeword)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed deleting user: {e}')
			return jsonify(success=False)
