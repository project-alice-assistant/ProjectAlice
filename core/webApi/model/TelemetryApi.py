#  Copyright (c) 2021
#
#  This file, TelemetryApi.py, is part of Project Alice.
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
from flask_classful import route

from core.util.Decorators import ApiAuthenticated
from core.webApi.model.Api import Api
from core.util.model.TelemetryType import TelemetryType


class TelemetryApi(Api):
	route_base = f'/api/{Api.version()}/telemetry/'


	@route('/', methods=['GET'])
	@ApiAuthenticated
	def get(self) -> Response:
		try:
			ttype: TelemetryType = TelemetryType(request.args.get('telemetryType', None))
			deviceId = request.args.get('deviceId', None)
			locationId = request.args.get('locationId', None)
			historyFrom = request.args.get('historyFrom', None)
			historyTo = request.args.get('historyTo', None)
			getAll = request.args.get('all', False)
			rows = self.TelemetryManager.getData(ttype=ttype, deviceId=deviceId, locationId=locationId, historyTo=historyTo, historyFrom=historyFrom, everything=getAll)
			return jsonify(rows)
		except Exception as e:
			self.logError(f'Failed getting telemetry data: {e}')
			return jsonify(success=False, message=str(e))


	@route('/overview/', methods=['GET'])
	@ApiAuthenticated
	def getOverview(self) -> Response:
		return jsonify(self.TelemetryManager.getAllCombinationsForAPI())
