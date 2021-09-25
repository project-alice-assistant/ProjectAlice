#  Copyright (c) 2021
#
#  This file, StateApi.py, is part of Project Alice.
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

from flask import jsonify
from flask_classful import route

from core.util.Decorators import ApiAuthenticated
from core.webApi.model.Api import Api


class StateApi(Api):
	route_base = f'/api/{Api.version()}/state/'


	def __init__(self):
		super().__init__()
		self.default_methods = ['GET']


	@route('/<statePath>/', methods=['GET'])
	@ApiAuthenticated
	def get(self, statePath: str) -> Response:
		try:
			state = self.StateManager.getState(statePath)
			if not state:
				raise Exception

			return jsonify(success=True, state=state.currentState.value)
		except:
			return jsonify(success=False, message=f'Unknown state: {statePath}')
