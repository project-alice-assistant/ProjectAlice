from flask import jsonify, request
from flask_classful import route

from core.interface.model.Api import Api
from core.util.Decorators import ApiAuthenticated



class TelemetryApi(Api):
	route_base = f'/api/{Api.version()}/telemetry/'


	def __init__(self):
		super().__init__()


	@route('/', methods=['GET'])
	@ApiAuthenticated
	def get(self):
		try:
			ttype = request.args.get('telemetryType', None)
			deviceId = request.args.get('deviceId', None)
			locationId = request.args.get('locationId', None)
			historyFrom = request.args.get('historyFrom', None)
			historyTo = request.args.get('historyTo', None)
			all = request.args.get('all', False)
			rows = self.TelemetryManager.getData(ttype=ttype, siteId=deviceId, locationId=locationId, historyTo=historyTo, historyFrom=historyFrom, all=all)
			rowarray_list = []
			for row in rows:
				d = dict(zip(row.keys(), row))  # a dict with column names as keys
				rowarray_list.append(d)
			return jsonify(rowarray_list)
		except Exception as e:
			self.logError(f'Failed getting telemetry data: {e}')
			return jsonify(success=False)


	@route('/overview/', methods=['GET'])
	@ApiAuthenticated
	def getOverview(self):
		return jsonify(self.TelemetryManager.getAllCombinationsForAPI())
