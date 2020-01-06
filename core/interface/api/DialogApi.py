from flask import jsonify, request
from flask_classful import route

from core.commons import constants
from core.interface.model.Api import Api
from core.util.Decorators import ApiAuthenticated


class DialogApi(Api):
	route_base = f'/api/{Api.version()}/dialog/'


	def __init__(self):
		super().__init__()


	@route('/say/', methods=['POST'])
	@ApiAuthenticated
	def say(self):
		try:
			siteId = request.form.get('siteId') if request.form.get('siteId', None) is not None else constants.DEFAULT_SITE_ID
			self.MqttManager.say(
				text=request.form.get('text'),
				client=siteId
			)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed speaking: {e}')
			return jsonify(success=False)
