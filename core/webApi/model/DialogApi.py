#  Copyright (c) 2021
#
#  This file, DialogApi.py, is part of Project Alice.
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

import json
from flask import Response, jsonify, request
from flask_classful import route
from paho.mqtt.client import MQTTMessage

from core.commons import constants
from core.device.model.DeviceAbility import DeviceAbility
from core.dialog.model.DialogSession import DialogSession
from core.util.Decorators import ApiAuthenticated
from core.webApi.model.Api import Api


class DialogApi(Api):
	route_base = f'/api/{Api.version()}/dialog/'


	def __init__(self):
		super().__init__()


	@route('/say/', methods=['POST'])
	@ApiAuthenticated
	def say(self) -> Response:
		try:
			deviceUid = request.form.get('deviceUid') if request.form.get('deviceUid', None) is not None else self.DeviceManager.getMainDevice().uid
			self.MqttManager.say(
				text=request.form.get('text'),
				deviceUid=deviceUid
			)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed speaking: {e}')
			return jsonify(success=False, message=str(e))


	@route('/ask/', methods=['POST'])
	@ApiAuthenticated
	def ask(self) -> Response:
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
	def process(self) -> Response:
		try:
			deviceUid = request.form.get('deviceUid') if request.form.get('deviceUid', None) is not None else self.DeviceManager.getMainDevice().uid

			user = self.UserManager.getUserByAPIToken(request.headers.get('auth', ''))
			session = self.DialogManager.newSession(deviceUid=deviceUid, user=user.name)
			session.deviceUid = deviceUid
			session.input = request.form.get('query')

			device = self.DeviceManager.getDevice(uid=deviceUid)
			if device:
				if not device.hasAbilities([DeviceAbility.PLAY_SOUND]):
					session.textOnly = True

				if not device.hasAbilities([DeviceAbility.CAPTURE_SOUND]):
					session.textInput = True
			else:
				session.textOnly = True
				session.textInput = True

			# Turn off the wakeword component
			self.MqttManager.publish(
				topic=constants.TOPIC_HOTWORD_TOGGLE_OFF,
				payload={
					'siteId'   : deviceUid,
					'sessionId': session.sessionId
				}
			)

			return self.publishText(session=session)
		except Exception as e:
			self.logError(f'Failed processing: {e}')
			return jsonify(success=False)


	@route('/continue/', methods=['POST'])
	@ApiAuthenticated
	def continueDialog(self) -> Response:
		try:
			deviceUid = request.form.get('deviceUid') if request.form.get('deviceUid', None) is not None else self.DeviceManager.getMainDevice().uid

			sessionId = request.form.get('sessionId')
			session = self.DialogManager.getSession(sessionId=sessionId)
			if not session:
				self.logError(f'Session not found: {sessionId}')
				return jsonify(success=False)

			session.deviceUid = deviceUid
			session.input = request.form.get('query')

			if not session or session.hasEnded:
				return self.process()

			self.DialogManager.startSessionTimeout(sessionId=session.sessionId)
			return self.publishText(session=session)
		except Exception as e:
			self.logError(f'Failed processing: {e}')
			return jsonify(success=False)


	def publishText(self, session: DialogSession) -> Response:
		message = MQTTMessage()
		message.payload = json.dumps({'sessionId': session.sessionId, 'siteId': session.deviceUid, 'text': session.input})
		session.extend(message=message)

		self.MqttManager.publish(
			topic=constants.TOPIC_TEXT_CAPTURED,
			payload={
				'sessionId' : session.sessionId,
				'text'      : session.input,
				'device'    : session.deviceUid,
				'likelihood': 1,
				'seconds'   : 1
			})
		return jsonify(success=True, sessionId=session.sessionId)
