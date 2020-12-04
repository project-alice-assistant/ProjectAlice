import traceback

from flask import jsonify, request
from flask_classful import route

from core.interface.model.Api import Api
from core.util.Decorators import ApiAuthenticated


class MyHomeApi(Api):
	route_base = f'/api/{Api.version()}/myHome/'


	def __init__(self):
		super().__init__()


	@route('/', methods=['GET'])
	@ApiAuthenticated
	def getData(self):
		try:
			return jsonify(data={
				'locations': {location.id: location.toDict() for location in self.LocationManager.locations.values()},
				'constructions': {construction.id: construction.toDict() for construction in self.LocationManager.constructions.values()},
				'furnitures': {furniture.id: furniture.toDict() for furniture in self.LocationManager.furnitures.values()}
			})
		except:
			traceback.print_exc()
			return jsonify(message='ERROR')


	@route('/locations/', methods=['PUT'])
	@ApiAuthenticated
	def addLocation(self):
		try:
			location = self.LocationManager.addNewLocation(data=request.json)
			if location:
				return jsonify(location=location.toDict())
			else:
				return jsonify(success=False)
		except Exception as e:
			self.logError(f'Something went wrong creating a new location {e}')
			return jsonify(message='ERROR')


	@route('/locations/<locationId>/savePosition/', methods=['PATCH'])
	@ApiAuthenticated
	def savePosition(self, locationId: str):
		try:
			return jsonify(success=self.WidgetManager.saveWidgetPosition(int(widgetId), request.json['x'], request.json['y']))
		except Exception as e:
			self.logError(f'Failed saving widget position: {e}')
			return jsonify(success=False)


	@route('/locations/<locationId>/saveSize/', methods=['PATCH'])
	@ApiAuthenticated
	def saveSize(self, locationId: str):
		try:
			return jsonify(success=self.WidgetManager.saveWidgetSize(int(widgetId), request.json['x'], request.json['y'], request.json['w'], request.json['h']))
		except Exception as e:
			self.logError(f'Failed saving widget size: {e}')
			return jsonify(success=False)
