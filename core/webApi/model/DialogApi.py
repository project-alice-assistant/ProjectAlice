import json

from flask import jsonify, request
from flask_classful import route
from paho.mqtt.client import MQTTMessage

from core.commons import constants
from core.webApi.model.Api import Api
from core.util.Decorators import ApiAuthenticated


class DialogApi(Api):
	route_base = f'/api/{Api.version()}/dialog/'


	def __init__(self):
		super().__init__()


	@route('/say/', methods=['POST'])
	@ApiAuthenticated
	def say(self):
		try:
			deviceUid = request.form.get('deviceUid') if request.form.get('deviceUid', None) is not None else self.DeviceManager.getMainDevice().uid
			self.MqttManager.say(
				text=request.form.get('text'),
				deviceUid=deviceUid
			)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed speaking: {e}')
			return jsonify(success=False)


	@route('/ask/', methods=['POST'])
	@ApiAuthenticated
	def ask(self):
		try:
			deviceUid = request.form.get('deviceUid') if request.form.get('deviceUid', None) is not None else self.DeviceManager.getMainDevice().uid
			self.MqttManager.ask(
				text=request.form.get('text'),
				deviceUid=deviceUid
			)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed asking: {e}')
			return jsonify(success=False)


	@route('/process/', methods=['POST'])
	@ApiAuthenticated
	def process(self):
		try:
			deviceUid = request.form.get('deviceUid') if request.form.get('deviceUid', None) is not None else self.DeviceManager.getMainDevice().uid

			user = self.UserManager.getUserByAPIToken(request.headers.get('auth', ''))
			session = self.DialogManager.newSession(deviceUid=deviceUid, user=user.name)

			# Turn off the wakeword component
			self.MqttManager.publish(
				topic=constants.TOPIC_HOTWORD_TOGGLE_OFF,
				payload={
					'siteId'   : deviceUid,
					'sessionId': session.sessionId
				}
			)

			message = MQTTMessage()
			message.payload = json.dumps({'sessionId': session.sessionId, 'siteId': deviceUid, 'text': request.form.get('query')})
			session.extend(message=message)

			self.MqttManager.publish(topic=constants.TOPIC_NLU_QUERY, payload={
				'input'    : request.form.get('query'),
				'intentFilter': list(self.DialogManager.getEnabledByDefaultIntents()),
				'sessionId': session.sessionId
			})
			return jsonify(success=True, sessionId=session.sessionId)
		except Exception as e:
			self.logError(f'Failed processing: {e}')
			return jsonify(success=False)


	@route('/continue/', methods=['POST'])
	@ApiAuthenticated
	def continueDialog(self):
		try:
			deviceUid = request.form.get('deviceUid') if request.form.get('deviceUid', None) is not None else self.DeviceManager.getMainDevice().uid

			sessionId = request.form.get('sessionId')
			session = self.DialogManager.getSession(sessionId=sessionId)

			if not session:
				return self.process()

			message = MQTTMessage()
			message.payload = json.dumps({'sessionId': session.sessionId, 'siteId': deviceUid, 'text': request.form.get('query')})
			session.extend(message=message)

			self.MqttManager.publish(topic=constants.TOPIC_NLU_QUERY, payload={
				'input'       : request.form.get('query'),
				'sessionId'   : session.sessionId,
				'intentFilter': session.intentFilter
			})
			return jsonify(success=True, sessionId=session.sessionId)
		except Exception as e:
			self.logError(f'Failed processing: {e}')
			return jsonify(success=False)
