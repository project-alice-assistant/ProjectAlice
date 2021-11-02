#  Copyright (c) 2021
#
#  This file, UsersApi.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:49 CEST

from flask import Response, jsonify, request

from core.user.model.AccessLevels import AccessLevel
from core.util.Decorators import ApiAuthenticated
from core.webApi.model.Api import Api


class UsersApi(Api):
	route_base = f'/api/{Api.version()}/users/'


	def __init__(self):
		super().__init__()


	@ApiAuthenticated
	def index(self) -> Response:
		return jsonify(data=[user.toJson() for user in self.UserManager.users.values()])


	@ApiAuthenticated
	def get(self, userId: int) -> Response:
		return jsonify(data=self.UserManager.getUserById(userId).toJson())


	@ApiAuthenticated
	def put(self) -> Response:
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
			return jsonify(success=False, message=str(e))


	@ApiAuthenticated
	def delete(self) -> Response:
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
			return jsonify(success=False, message=str(e))
