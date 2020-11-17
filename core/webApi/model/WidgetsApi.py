from flask import jsonify, request
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


	@route('/', methods=['PUT'])
	@ApiAuthenticated
	def addWidget(self):
		try:
			return jsonify(widgets=self.WidgetManager.widgetInstances)
		except Exception as e:
			self.logError(f'Failed adding widget instance: {e}')
			return jsonify(success=False)


	@route('/pages/', methods=['GET'])
	@ApiAuthenticated
	def getPages(self):
		try:
			pages = {page.id: str(page) for page in self.WidgetManager.pages.values()}
			return jsonify(pages=pages)
		except Exception as e:
			self.logError(f'Failed retrieving widget pages: {e}')
			return jsonify(success=False)


	@route('/pages/<pageId>/', methods=['DELETE'])
	@ApiAuthenticated
	def removePage(self, pageId: str):
		try:
			if int(pageId) == 0:
				raise Exception

			self.WidgetManager.removePage(int(pageId))
			pages = {page.id: str(page) for page in self.WidgetManager.pages.values()}
			return jsonify(pages=pages)
		except Exception as e:
			self.logError(f'Failed removing widget page: {e}')
			return jsonify(success=False)


	@route('/pages/<pageId>/', methods=['PATCH'])
	@ApiAuthenticated
	def updatePageIcon(self, pageId: str):
		try:
			self.WidgetManager.updatePageIcon(int(pageId), request.json['newIcon'])
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed saving widget page icon: {e}')
			return jsonify(success=False)


	@route('/templates/')
	def getTemplates(self):
		try:
			return jsonify(widgets=self.WidgetManager.widgetTemplates)
		except Exception as e:
			self.logError(f'Failed retrieving widget templates: {e}')
			return jsonify(success=False)


	@route('/addPage/', methods=['PUT'])
	@ApiAuthenticated
	def put(self):
		try:
			page = self.WidgetManager.addPage()
			if not page:
				raise Exception

			return jsonify(newpage=str(page))
		except Exception as e:
			self.logError(f'Failed adding new widget page: {e}')
			return jsonify(success=False)
