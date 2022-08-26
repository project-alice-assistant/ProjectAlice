#  Copyright (c) 2021
#
#  This file, Api.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:48 CEST
from flask import jsonify
from flask_classful import FlaskView

from core.base.model.ProjectAliceObject import ProjectAliceObject


class Api(FlaskView, ProjectAliceObject):
	default_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
	_version = '1.0.1'


	def before_request(self, _name: str, **_kwargs):
		# refuse requests if Alice is not yet booted
		if not self.ProjectAlice.isBooted:
			return jsonify(success=False, data=423)


	@classmethod
	def version(cls) -> str:
		return f'v{cls._version}'
