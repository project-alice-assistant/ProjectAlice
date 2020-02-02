import json
import uuid

from flask import jsonify, request
from flask_classful import route
from paho.mqtt.client import MQTTMessage

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
			self.log.error(f'Failed speaking: {e}')
			return jsonify(success=False)


	@route('/ask/', methods=['POST'])
	@ApiAuthenticated
	def ask(self):
		try:
			siteId = request.form.get('siteId') if request.form.get('siteId', None) is not None else constants.DEFAULT_SITE_ID
			self.MqttManager.ask(
				text=request.form.get('text'),
				client=siteId
			)
			return jsonify(success=True)
		except Exception as e:
			self.log.error(f'Failed asking: {e}')
			return jsonify(success=False)


	@route('/process/', methods=['POST'])
	@ApiAuthenticated
	def process(self):
		try:
			siteId = request.form.get('siteId') if request.form.get('siteId', None) is not None else constants.DEFAULT_SITE_ID

			sessionId = str(uuid.uuid4())
			message = MQTTMessage()
			message.payload = json.dumps({'sessionId': sessionId, 'siteId': siteId})

			session = self.DialogSessionManager.addSession(sessionId=sessionId, message=message)
			session.isAPIGenerated = True
			self.MqttManager.publish(topic=constants.TOPIC_NLU_QUERY, payload={
				'input'    : request.form.get('query'),
				'sessionId': session.sessionId
			})
			return jsonify(success=True)
		except Exception as e:
			self.log.error(f'Failed processing: {e}')
			return jsonify(success=False)
