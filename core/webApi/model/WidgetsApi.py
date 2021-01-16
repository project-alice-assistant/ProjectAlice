from flask import jsonify, request, send_from_directory
from flask_classful import route

from core.webApi.model.Api import Api
from core.util.Decorators import ApiAuthenticated


class WidgetsApi(Api):
	route_base = f'/api/{Api.version()}/widgets/'


	def __init__(self):
		super().__init__()


	@route('/', methods=['GET'])
	def getWidgets(self):
		try:
			widgets = {widget.id: widget.toDict(self.UserManager.apiTokenValid(request.headers.get('auth', ''))) for widget in self.WidgetManager.widgets.values()}
			return jsonify(widgets=widgets)

		except Exception as e:
			self.logError(f'Failed retrieving widget instances: {e}')
			return jsonify(success=False)


	@route('/', methods=['PUT'])
	@ApiAuthenticated
	def addWidget(self):
		try:
			skillName = request.json['skillName']
			widgetName = request.json['widgetName']
			pageId = request.json['pageId']
			widget = self.WidgetManager.addWidget(skillName, widgetName, pageId)
			if not widget:
				raise Exception

			return jsonify(widget=widget.toDict())
		except Exception as e:
			self.logError(f'Failed adding widget instance: {e}')
			return jsonify(success=False)


	@route('/resources/<skillName>/<widgetName>.js/', methods=['GET'])
	def getJS(self, skillName: str, widgetName: str):
		try:
			return send_from_directory(f'{self.Commons.rootDir()}/skills/{skillName}/widgets/js', f'{widgetName}.js')
		except Exception as e:
			self.logError(f'Error fetching widget JS resource {e}')
			return jsonify(success=False)


	@route('/resources/<skillName>/<widgetName>.css', methods=['GET'])
	def getCSS(self, skillName: str, widgetName: str):
		try:
			return send_from_directory(f'{self.Commons.rootDir()}/skills/{skillName}/widgets/css', f'{widgetName}.css')
		except Exception as e:
			self.logError(f'Error fetching widget CSS resource {e}')
			return jsonify(success=False)


	@route('/<widgetId>/', methods=['DELETE'])
	@ApiAuthenticated
	def removeWidget(self, widgetId: str):
		try:
			self.WidgetManager.removeWidget(int(widgetId))
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed removing widget: {e}')
			return jsonify(success=False)


	@route('/pages/', methods=['GET'])
	def getPages(self):
		try:
			return jsonify(pages={page.id: page.toDict() for page in self.WidgetManager.pages.values()})
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
			pages = {page.id: page.toDict() for page in self.WidgetManager.pages.values()}
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

			return jsonify(newpage=page.toDict())
		except Exception as e:
			self.logError(f'Failed adding new widget page: {e}')
			return jsonify(success=False)


	@route('/<widgetId>/savePosition/', methods=['PATCH'])
	@ApiAuthenticated
	def savePosition(self, widgetId: str):
		try:
			return jsonify(success=self.WidgetManager.saveWidgetPosition(int(widgetId), request.json['x'], request.json['y']))
		except Exception as e:
			self.logError(f'Failed saving widget position: {e}')
			return jsonify(success=False)


	@route('/<widgetId>/saveSize/', methods=['PATCH'])
	@ApiAuthenticated
	def saveSize(self, widgetId: str):
		try:
			return jsonify(success=self.WidgetManager.saveWidgetSize(int(widgetId), request.json['x'], request.json['y'], request.json['w'], request.json['h']))
		except Exception as e:
			self.logError(f'Failed saving widget size: {e}')
			return jsonify(success=False)


	@route('/<widgetId>/', methods=['PATCH'])
	@ApiAuthenticated
	def saveParams(self, widgetId: str):
		try:
			return jsonify(success=self.WidgetManager.saveWidgetParams(int(widgetId), request.json))
		except Exception as e:
			self.logError(f'Failed saving widget paraams: {e}')
			return jsonify(success=False)