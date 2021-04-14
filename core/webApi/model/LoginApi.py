#  Copyright (c) 2021
#
#  This file, LoginApi.py, is part of Project Alice.
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
		except Exception as e:
			return jsonify(message=f'ERROR: Unauthorized {e}')


	@route('/checkToken/', methods=['POST'])
	@ApiAuthenticated
	def checkToken(self):
		try:
			return jsonify(success=True, authLevel=self.UserManager.apiTokenLevel(request.headers.get('auth')))
		except Exception as e:
			return jsonify(message=f'ERROR: Unauthorized {e}')
