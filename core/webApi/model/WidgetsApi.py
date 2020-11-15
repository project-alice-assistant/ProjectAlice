from flask import jsonify
from flask_classful import route

from core.interface.model.Api import Api
from core.util.Decorators import ApiAuthenticated


class WidgetsApi(Api):
	route_base = f'/api/{Api.version()}/widgets/'


	def __init__(self):
		super().__init__()


	@route('/')
	@ApiAuthenticated
	def getWidgets(self):
		try:
			return jsonify(widgets=self.WidgetManager.widgetInstances)
		except Exception as e:
			self.logError(f'Failed retrieving widget instances: {e}')
			return jsonify(success=False)


	@route('/pages/')
	@ApiAuthenticated
	def getPages(self):
		try:
			return jsonify(pages=self.WidgetManager.pages)
		except Exception as e:
			self.logError(f'Failed retrieving widget pages: {e}')
			return jsonify(success=False)


	@route('/available/')
	def getAvailable(self):
		try:
			return jsonify(widgets=self.WidgetManager.getAvailableWidgets())
		except Exception as e:
			self.logError(f'Failed retrieving widgets: {e}')
			return jsonify(success=False)
