import json
import traceback
import uuid
from pathlib import Path
from typing import List

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import random
import re

from core.base.model.Intent import Intent
from core.base.model.Manager import Manager
from core.commons import constants
from core.device.model.Device import Device


class MqttManager(Manager):

	DEFAULT_CLIENT_EXTENSION = '@mqtt'
	TOPIC_AUDIO_FRAME = constants.TOPIC_AUDIO_FRAME.replace('{}', '+')

	def __init__(self):
		super().__init__()

		self._mqttClient = mqtt.Client()
		self._multiDetectionsHolder = list()
		self._deactivatedIntents = list()

		self._audioFrameRegex = re.compile(self.TOPIC_AUDIO_FRAME.replace('+', '(.*)'))
		self._wakewordDetectedRegex = re.compile(constants.TOPIC_WAKEWORD_DETECTED.replace('{}', '(.*)'))
		self._vadUpRegex = re.compile(constants.TOPIC_VAD_UP.replace('{}', '(.*)'))
		self._vadDownRegex = re.compile(constants.TOPIC_VAD_DOWN.replace('{}', '(.*)'))

		self._INTENT_RANDOM_ANSWER = Intent('UserRandomAnswer', isProtected=True)


	def onStart(self):
		super().onStart()

		self._mqttClient.on_message = self.onMqttMessage
		self._mqttClient.on_connect = self.onConnect
		self._mqttClient.on_log = self.onLog

		self._mqttClient.message_callback_add(constants.TOPIC_HOTWORD_DETECTED, self.onHotwordDetected)
		for username in self.UserManager.getAllUserNames():
			self._mqttClient.message_callback_add(constants.TOPIC_WAKEWORD_DETECTED.replace('{user}', username), self.onHotwordDetected)

		self._mqttClient.message_callback_add(constants.TOPIC_VAD_UP.format(self.ConfigManager.getAliceConfigByName('deviceName')), self.onVADUp)
		self._mqttClient.message_callback_add(constants.TOPIC_VAD_DOWN.format(self.ConfigManager.getAliceConfigByName('deviceName')), self.onVADDown)

		self._mqttClient.message_callback_add(constants.TOPIC_SESSION_STARTED, self.sessionStarted)
		self._mqttClient.message_callback_add(constants.TOPIC_ASR_START_LISTENING, self.startListening)
		self._mqttClient.message_callback_add(constants.TOPIC_ASR_STOP_LISTENING, self.stopListening)
		self._mqttClient.message_callback_add(constants.TOPIC_ASR_TOGGLE_ON, self.asrToggleOn)
		self._mqttClient.message_callback_add(constants.TOPIC_ASR_TOGGLE_OFF, self.asrToggleOff)
		self._mqttClient.message_callback_add(constants.TOPIC_INTENT_PARSED, self.intentParsed)
		self._mqttClient.message_callback_add(constants.TOPIC_TEXT_CAPTURED, self.captured)
		self._mqttClient.message_callback_add(constants.TOPIC_TTS_SAY, self.intentSay)
		self._mqttClient.message_callback_add(constants.TOPIC_TTS_FINISHED, self.sayFinished)
		self._mqttClient.message_callback_add(constants.TOPIC_SESSION_ENDED, self.sessionEnded)
		self._mqttClient.message_callback_add(constants.TOPIC_CONTINUE_SESSION, self.continueSession)
		self._mqttClient.message_callback_add(constants.TOPIC_INTENT_NOT_RECOGNIZED, self.intentNotRecognized)
		self._mqttClient.message_callback_add(constants.TOPIC_SESSION_QUEUED, self.sessionQueued)
		self._mqttClient.message_callback_add(constants.TOPIC_NLU_QUERY, self.nluQuery)
		self._mqttClient.message_callback_add(constants.TOPIC_PARTIAL_TEXT_CAPTURED, self.nluPartialCapture)
		self._mqttClient.message_callback_add(constants.TOPIC_HOTWORD_TOGGLE_ON, self.hotwordToggleOn)
		self._mqttClient.message_callback_add(constants.TOPIC_HOTWORD_TOGGLE_OFF, self.hotwordToggleOff)
		self._mqttClient.message_callback_add(constants.TOPIC_END_SESSION, self.eventEndSession)
		self._mqttClient.message_callback_add(constants.TOPIC_START_SESSION, self.startSession)
		self._mqttClient.message_callback_add(constants.TOPIC_DEVICE_HEARTBEAT, self.deviceHeartbeat)
		self._mqttClient.message_callback_add(constants.TOPIC_TOGGLE_FEEDBACK_ON, self.toggleFeedback)
		self._mqttClient.message_callback_add(constants.TOPIC_TOGGLE_FEEDBACK_OFF, self.toggleFeedback)
		self._mqttClient.message_callback_add(constants.TOPIC_NLU_INTENT_NOT_RECOGNIZED, self.nluIntentNotRecognized)
		self._mqttClient.message_callback_add(constants.TOPIC_NLU_ERROR, self.nluError)

		self._mqttClient.message_callback_add(constants.TOPIC_PLAY_BYTES.format(self.ConfigManager.getAliceConfigByName('deviceName')), self.topicPlayBytes)
		self._mqttClient.message_callback_add(constants.TOPIC_PLAY_BYTES_FINISHED.format(self.ConfigManager.getAliceConfigByName('deviceName')), self.topicPlayBytesFinished)

		for device in self.getAliceTypeDevices():
			self.MqttManager.mqttClient.message_callback_add(constants.TOPIC_VAD_UP.format(device.siteId), self.MqttManager.onVADUp)
			self.MqttManager.mqttClient.message_callback_add(constants.TOPIC_VAD_DOWN.format(device.siteId), self.MqttManager.onVADDown)

			self._mqttClient.message_callback_add(constants.TOPIC_PLAY_BYTES.format(device.siteId), self.MqttManager.topicPlayBytes)
			self._mqttClient.message_callback_add(constants.TOPIC_PLAY_BYTES_FINISHED.format(device.siteId), self.MqttManager.topicPlayBytesFinished)

		self.connect()


	def onStop(self):
		super().onStop()
		self.disconnect()


	def onLog(self, _client, _userdata, level, buf):
		if level != 16:
			self.logError(buf)


	def onConnect(self, _client, _userdata, _flags, _rc):

		subscribedEvents = [
			(constants.TOPIC_SESSION_ENDED, 0),
			(constants.TOPIC_SESSION_STARTED, 0),
			(constants.TOPIC_HOTWORD_DETECTED, 0),
			(constants.TOPIC_INTENT_NOT_RECOGNIZED, 0),
			(constants.TOPIC_INTENT_PARSED, 0),
			(constants.TOPIC_TTS_FINISHED, 0),
			(constants.TOPIC_ASR_START_LISTENING, 0),
			(constants.TOPIC_ASR_STOP_LISTENING, 0),
			(constants.TOPIC_TTS_SAY, 0),
			(constants.TOPIC_TEXT_CAPTURED, 0),
			(constants.TOPIC_PARTIAL_TEXT_CAPTURED, 0),
			(constants.TOPIC_HOTWORD_TOGGLE_ON, 0),
			(constants.TOPIC_HOTWORD_TOGGLE_OFF, 0),
			(constants.TOPIC_NLU_QUERY, 0),
			(constants.TOPIC_CONTINUE_SESSION, 0),
			(constants.TOPIC_END_SESSION, 0),
			(constants.TOPIC_DEVICE_HEARTBEAT, 0),
			(constants.TOPIC_ASR_TOGGLE_ON, 0),
			(constants.TOPIC_ASR_TOGGLE_OFF, 0),
			(constants.TOPIC_TOGGLE_FEEDBACK_ON, 0),
			(constants.TOPIC_TOGGLE_FEEDBACK_OFF, 0),
			(constants.TOPIC_NLU_INTENT_NOT_RECOGNIZED, 0),
			(constants.TOPIC_START_SESSION, 0),
			(constants.TOPIC_NLU_ERROR, 0),
			(self.TOPIC_AUDIO_FRAME, 0)
		]

		for username in self.UserManager.getAllUserNames():
			subscribedEvents.append((constants.TOPIC_WAKEWORD_DETECTED.format(username), 0))

		subscribedEvents.append((constants.TOPIC_VAD_UP.format(self.ConfigManager.getAliceConfigByName('deviceName')), 0))
		subscribedEvents.append((constants.TOPIC_VAD_DOWN.format(self.ConfigManager.getAliceConfigByName('deviceName')), 0))

		subscribedEvents.append((constants.TOPIC_PLAY_BYTES.format(self.ConfigManager.getAliceConfigByName('deviceName')), 0))
		subscribedEvents.append((constants.TOPIC_PLAY_BYTES_FINISHED.format(self.ConfigManager.getAliceConfigByName('deviceName')), 0))

		for device in self.getAliceTypeDevices():
			subscribedEvents.append((constants.TOPIC_VAD_UP.format(device.siteId), 0))
			subscribedEvents.append((constants.TOPIC_VAD_DOWN.format(device.siteId), 0))

			subscribedEvents.append((constants.TOPIC_PLAY_BYTES.format(device.siteId), 0))
			subscribedEvents.append((constants.TOPIC_PLAY_BYTES_FINISHED.format(device.siteId), 0))

		self._mqttClient.subscribe(subscribedEvents)
		self.toggleFeedbackSounds()


	def connect(self):
		if self.ConfigManager.getAliceConfigByName('mqttUser') and self.ConfigManager.getAliceConfigByName('mqttPassword'):
			self._mqttClient.username_pw_set(self.ConfigManager.getAliceConfigByName('mqttUser'), self.ConfigManager.getAliceConfigByName('mqttPassword'))

		if self.ConfigManager.getAliceConfigByName('mqttTLSFile'):
			self._mqttClient.tls_set(certfile=self.ConfigManager.getAliceConfigByName('mqttTLSFile'))
			self._mqttClient.tls_insecure_set(False)

		self._mqttClient.connect(self.ConfigManager.getAliceConfigByName('mqttHost'), int(self.ConfigManager.getAliceConfigByName('mqttPort')))

		self._mqttClient.loop_start()


	def disconnect(self):
		self._mqttClient.loop_stop()
		self._mqttClient.disconnect()


	def reconnect(self):
		self.disconnect()
		self.connect()


	def subscribeSkillIntents(self, intents: list):
		# Have to send them one at a time, as intents is a list of Intent objects and mqtt doesn't want that
		for intent in intents:
			self.mqttClient.subscribe(str(intent))


	def unsubscribeSkillIntents(self, intents: list):
		# Have to send them one at a time, as intents is a list of Intent objects and mqtt doesn't want that
		for intent in intents:
			self.mqttClient.unsubscribe(str(intent))


	def onMqttMessage(self, _client, _userdata, message: mqtt.MQTTMessage):
		try:
			if self._audioFrameRegex.match(message.topic):
				self.broadcast(
					method=constants.EVENT_AUDIO_FRAME,
					exceptions=[self.name],
					propagateToSkills=True,
					message=message,
					siteId=message.topic.replace('hermes/audioServer/', '').replace('/audioFrame', '')
				)
				return

			if message.topic == constants.TOPIC_INTENT_PARSED:
				return

			payload = self.Commons.payload(message)
			sessionId = self.Commons.parseSessionId(message)

			session = self.DialogManager.getSession(sessionId)
			if session:
				session.update(message)
				if self.MultiIntentManager.processMessage(message):
					return

			if message.topic == constants.TOPIC_TEXT_CAPTURED and session:
				return

			if not session:  # It is a device trying to communicate with Alice
				session = self.DeviceManager.deviceMessage(message)
				self.broadcast(method=constants.EVENT_MESSAGE, exceptions=[self.name], session=session)
				self.SkillManager.dispatchMessage(session=session)
				return

			self.logDebug(f'Using probability threshold of {session.probabilityThreshold}')

			self.broadcast(method=constants.EVENT_INTENT, exceptions=[self.name], propagateToSkills=True, session=session)

			if 'intent' in payload and float(payload['intent']['confidenceScore']) < session.probabilityThreshold:
				self.logDebug(f'Intent **{message.topic}** detected but confidence score too low ({payload["intent"]["confidenceScore"]})')
				if session.notUnderstood <= self.ConfigManager.getAliceConfigByName('notUnderstoodRetries'):
					session.notUnderstood = session.notUnderstood + 1

					self.continueDialog(
						sessionId=sessionId,
						text=self.TalkManager.randomTalk('notUnderstood', skill='system'),
						probabilityThreshold=session.probabilityThreshold,
						intentFilter=session.intentFilter
					)

					self.broadcast(method=constants.EVENT_INTENT_NOT_RECOGNIZED, exceptions=[self.name], propagateToSkills=True, session=session)
				else:
					session.notUnderstood = 0
					self.endDialog(
						sessionId=sessionId,
						text=self.TalkManager.randomTalk('notUnderstoodEnd', skill='system')
					)
				return

			skill = self.SkillManager.getSkillInstance('ContextSensitive')
			if skill:
				skill.addToMessageHistory(session)

			consumed = self.SkillManager.dispatchMessage(session=session)
			if consumed:
				return

			self.logWarning(f"Intent **{message.topic}** wasn't consumed by any skill")
			if session.notUnderstood <= self.ConfigManager.getAliceConfigByName('notUnderstoodRetries'):
				session.notUnderstood = session.notUnderstood + 1

				self.continueDialog(
					sessionId=sessionId,
					text=self.TalkManager.randomTalk('notUnderstood', skill='system'),
					intentFilter=session.intentFilter
				)
			else:
				session.notUnderstood = 0
				self.endDialog(
					sessionId=sessionId,
					text=self.TalkManager.randomTalk('notUnderstoodEnd', skill='system')
				)
			return

		except Exception as e:
			self.logError(f'Error in onMessage: {e}')
			traceback.print_exc()


	def onHotwordDetected(self, _client, _data, msg):
		siteId = self.Commons.parseSiteId(msg)
		payload = self.Commons.payload(msg)

		if not self._multiDetectionsHolder:
			self.ThreadManager.doLater(interval=0.5, func=self.handleMultiDetection)

		self._multiDetectionsHolder.append(payload['siteId'])

		user = constants.UNKNOWN_USER
		if payload['modelType'] == 'personal':
			speaker = payload['modelId']
			users = {name.lower(): user for name, user in self.UserManager.users.items()}
			if speaker in users:
				user = users[speaker].name

		if user == constants.UNKNOWN_USER:
			self.broadcast(method=constants.EVENT_HOTWORD, exceptions=[self.name], propagateToSkills=True, siteId=siteId, user=user)
		else:
			self.broadcast(method=constants.EVENT_WAKEWORD, exceptions=[self.name], propagateToSkills=True, siteId=siteId, user=user)


	def handleMultiDetection(self):
		if len(self._multiDetectionsHolder) <= 1:
			self._multiDetectionsHolder = list()
			return

		sessions = self.DialogManager.sessions
		for sessionId in sessions:
			payload = self.Commons.payload(sessions[sessionId].message)
			if payload['siteId'] != self._multiDetectionsHolder[0]:
				self.endSession(sessionId=sessionId)

		self._multiDetectionsHolder = list()


	def hotwordToggleOn(self, _client, _data, msg: mqtt.MQTTMessage):
		siteId = self.Commons.parseSiteId(msg)
		session = self.DialogManager.getSession(self.Commons.parseSessionId(msg))
		self.broadcast(method=constants.EVENT_HOTWORD_TOGGLE_ON, exceptions=[constants.DUMMY], propagateToSkills=True, siteId=siteId, session=session)


	def hotwordToggleOff(self, _client, _data, msg: mqtt.MQTTMessage):
		siteId = self.Commons.parseSiteId(msg)
		session = self.DialogManager.getSession(self.Commons.parseSessionId(msg))
		self.broadcast(method=constants.EVENT_HOTWORD_TOGGLE_OFF, exceptions=[constants.DUMMY], propagateToSkills=True, siteId=siteId, session=session)


	def sessionStarted(self, _client, _data, msg: mqtt.MQTTMessage):
		session = self.DialogManager.getSession(sessionId=self.Commons.parseSessionId(msg))

		if session:
			session.update(msg)
			self.broadcast(method=constants.EVENT_SESSION_STARTED, exceptions=[self.name], propagateToSkills=True, session=session)


	def sessionQueued(self, _client, _data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogManager.addSession(sessionId=sessionId, message=msg)

		if session:
			session.update(msg)
			self.broadcast(method=constants.EVENT_SESSION_QUEUED, exceptions=[self.name], propagateToSkills=True, session=session)


	def nluQuery(self, _client, _data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		siteId = self.Commons.parseSiteId(msg)

		session = self.DialogManager.getSession(sessionId)
		if not session:
			session = self.DialogManager.newSession(siteId=siteId)
		else:
			session.update(msg)

		self.broadcast(method=constants.EVENT_NLU_QUERY, exceptions=[self.name], propagateToSkills=True, session=session)


	def asrToggleOn(self, _client, _data, msg: mqtt.MQTTMessage):
		self.broadcast(method=constants.EVENT_ASR_TOGGLE_ON, exceptions=[self.name], propagateToSkills=True, siteId=self.Commons.parseSiteId(msg))


	def asrToggleOff(self, _client, _data, msg: mqtt.MQTTMessage):
		self.broadcast(method=constants.EVENT_ASR_TOGGLE_OFF, exceptions=[self.name], propagateToSkills=True, siteId=self.Commons.parseSiteId(msg))


	def startListening(self, _client, _data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogManager.getSession(sessionId=sessionId)

		if session:
			session.update(msg)
			self.broadcast(method=constants.EVENT_START_LISTENING, exceptions=[self.name], propagateToSkills=True, session=session)


	def stopListening(self, _client, _data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogManager.getSession(sessionId=sessionId)

		if session:
			session.update(msg)
			self.broadcast(method=constants.EVENT_STOP_LISTENING, exceptions=[self.name], propagateToSkills=True, session=session)


	def captured(self, _client, _data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogManager.getSession(sessionId=sessionId)

		if session:
			session.update(msg)
			self.broadcast(method=constants.EVENT_CAPTURED, exceptions=[self.name], propagateToSkills=True, session=session)


	def intentParsed(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogManager.getSession(sessionId=sessionId)

		if session:
			session.update(msg)

			intent = Intent(session.payload['intent']['intentName'])
			if str(intent) in self._deactivatedIntents:
				# If the intent was deactivated, let's try the next possible alternative, if any
				alternative = dict()

				if 'alternatives' in session.payload:
					for alt in session.payload['alternatives']:
						if str(Intent(alt["intentName"])) in self._deactivatedIntents or alt['confidenceScore'] < self.ConfigManager.getAliceConfigByName('probabilityThreshold'):
							continue
						alternative = alt
						break

				if alternative:
					self.broadcast(method=constants.EVENT_INTENT_PARSED, exceptions=[self.name], propagateToSkills=True, session=session)
					intent = Intent(alternative['intentName'])
					payload = session.payload
					payload['slots'] = alternative['slots']
				else:
					payload = session.payload

				message = mqtt.MQTTMessage(topic=str.encode(str(intent)))
				message.payload = json.dumps(payload)
				self.onMqttMessage(_client=client, _userdata=data, message=message)
			else:
				self.broadcast(method=constants.EVENT_INTENT_PARSED, exceptions=[self.name], propagateToSkills=True, session=session)


	def continueSession(self, _client, _data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogManager.getSession(sessionId)
		if session:
			session.update(msg)
			self.broadcast(method=constants.EVENT_CONTINUE_SESSION, exceptions=[self.name], propagateToSkills=True, session=session)
		else:
			self.logWarning(f'Was asked to continue session with id **{sessionId}** but session does not exist')


	def sessionEnded(self, _client, data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogManager.getSession(sessionId)

		if not session:
			return

		session.hasEnded = True
		session.update(msg)

		reason = session.payload['termination']['reason']
		if reason:
			if reason == 'abortedByUser':
				self.broadcast(method=constants.EVENT_USER_CANCEL, exceptions=[self.name], propagateToSkills=True, session=session)
			elif reason == 'timeout':
				self.logWarning(f'Session "{session.sessionId}" ended after timing out')
				self.broadcast(method=constants.EVENT_SESSION_TIMEOUT, exceptions=[self.name], propagateToSkills=True, session=session)
			elif reason == 'intentNotRecognized':
				# This should never trigger, as "sendIntentNotRecognized" is always set to True, but we never know
				self.intentNotRecognized(None, data, msg)
			elif reason == 'error':
				self.logError(f'Session "{session.sessionId}" ended with an unrecoverable error: {session.payload["termination"]["error"]}')
				self.broadcast(method=constants.EVENT_SESSION_ERROR, exceptions=[self.name], propagateToSkills=True, session=session)
			else:
				self.broadcast(method=constants.EVENT_SESSION_ENDED, exceptions=[self.name], propagateToSkills=True, session=session)
				return

		self.broadcast(method=constants.EVENT_SESSION_ENDED, exceptions=[self.name], propagateToSkills=True, session=session)


	def intentSay(self, _client, _data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		payload = self.Commons.payload(msg)

		session = self.DialogManager.getSession(sessionId)
		if session:
			session.update(msg)
		else:
			session = self.DialogManager.newSession(siteId=self.Commons.parseSiteId(msg), message=msg)

		if 'text' in payload and not payload.get('isHotwordNotification', False):
			skill = self.SkillManager.getSkillInstance('ContextSensitive')
			if skill:
				skill.addAliceChat(text=payload['text'], siteId=session.siteId)

		self.broadcast(method=constants.EVENT_SAY, exceptions=[self.name], propagateToSkills=True, session=session)


	def sayFinished(self, _client, _data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		uid = ''
		session = self.DialogManager.getSession(sessionId)
		if session:
			session.update(msg)
			uid = session.payload['id']

		self.broadcast(method=constants.EVENT_SAY_FINISHED, exceptions=[self.name], propagateToSkills=True, session=session, uid=uid)


	def intentNotRecognized(self, _client, _data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogManager.getSession(sessionId)

		if not session:
			self.ask(text=self.TalkManager.randomTalk('notUnderstood', skill='system'))
		else:
			session.update(msg)

			if session.notUnderstood <= self.ConfigManager.getAliceConfigByName('notUnderstoodRetries'):
				session.notUnderstood = session.notUnderstood + 1
				self.continueDialog(
					sessionId=sessionId,
					text=self.TalkManager.randomTalk('notUnderstood', skill='system'),
					intentFilter=session.intentFilter
				)
			else:
				session.notUnderstood = 0
				self.endDialog(sessionId=sessionId, text=self.TalkManager.randomTalk('notUnderstoodEnd', skill='system'))

			self.broadcast(method=constants.EVENT_INTENT_NOT_RECOGNIZED, exceptions=[self.name], propagateToSkills=True, session=session)


	def nluPartialCapture(self, _client, _data, msg: mqtt.MQTTMessage):
		session = self.DialogManager.getSession(self.Commons.parseSessionId(msg))

		if session:
			session.update(msg)
			payload = self.Commons.payload(msg)
			self.broadcast(method=constants.EVENT_PARTIAL_TEXT_CAPTURED, exceptions=[self.name], propagateToSkills=True, session=session, text=payload['text'], likelihood=payload['likelihood'], seconds=payload['seconds'])


	def nluIntentNotRecognized(self, _client, _data, msg: mqtt.MQTTMessage):
		session = self.DialogManager.getSession(self.Commons.parseSessionId(msg))

		if session:
			session.update(msg)
			self.broadcast(method=constants.EVENT_NLU_INTENT_NOT_RECOGNIZED, exceptions=[self.name], propagateToSkills=True, session=session)


	def nluError(self, _client, _data, msg: mqtt.MQTTMessage):
		session = self.DialogManager.getSession(self.Commons.parseSessionId(msg))

		if session:
			session.update(msg)
			self.broadcast(method=constants.EVENT_NLU_ERROR, exceptions=[self.name], propagateToSkills=True, session=session)


	def startSession(self, _client, _data, msg: mqtt.MQTTMessage):
		self.broadcast(
			method=constants.EVENT_START_SESSION,
			exceptions=[self.name],
			propagateToSkills=True,
			siteId=self.Commons.parseSiteId(msg),
			payload=self.Commons.payload(msg)
		)


	def onVADUp(self, _client, _data, msg: mqtt.MQTTMessage):
		siteId = self.Commons.parseSiteId(msg)
		self.broadcast(
			method=constants.EVENT_VAD_UP,
			exceptions=[self.name],
			propagateToSkills=True,
			siteId=siteId
		)


	def onVADDown(self, _client, _data, msg: mqtt.MQTTMessage):
		siteId = self.Commons.parseSiteId(msg)
		self.broadcast(method=constants.EVENT_VAD_DOWN, exceptions=[self.name], propagateToSkills=True, siteId=siteId)


	def eventEndSession(self, _client, _data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogManager.getSession(sessionId)
		if session:
			session.update(msg)
			self.broadcast(method=constants.EVENT_END_SESSION, exceptions=[self.name], propagateToSkills=True, session=session)


	def topicPlayBytes(self, _client, _data, msg: mqtt.MQTTMessage):
		"""
		SessionId is completly custom and does not belong in the Hermes Protocol
		:param _client:
		:param _data:
		:param msg:
		:return:
		"""
		count = msg.topic.count('/')
		if count > 4:
			requestId = msg.topic.rsplit('/')[-1]
			sessionId = msg.topic.rsplit('/')[-2]
		else:
			requestId = msg.topic.rsplit('/')[-1]
			sessionId = None

		siteId = self.Commons.parseSiteId(msg)
		self.broadcast(method=constants.EVENT_PLAY_BYTES, exceptions=self.name, propagateToSkills=True, requestId=requestId, payload=msg.payload, siteId=siteId, sessionId=sessionId)


	def topicPlayBytesFinished(self, _client, _data, msg: mqtt.MQTTMessage):
		requestId = msg.topic.rsplit('/')[-1]
		siteId = self.Commons.parseSiteId(msg)
		sessionId = self.Commons.parseSessionId(msg)
		self.broadcast(method=constants.EVENT_PLAY_BYTES_FINISHED, exceptions=self.name, propagateToSkills=True, requestId=requestId, siteId=siteId, sessionId=sessionId)


	def deviceHeartbeat(self, _client, _data, msg: mqtt.MQTTMessage):
		payload = self.Commons.payload(msg)
		uid = payload.get('uid', None)
		if not uid:
			self.logWarning('Received a device heartbeat without uid')
			return

		siteId = self.Commons.parseSiteId(msg)
		self.broadcast(method=constants.EVENT_DEVICE_HEARTBEAT, exceptions=[self.name], propagateToSkills=True, uid=uid, siteId=siteId)


	def toggleFeedback(self, _client, _data, msg: mqtt.MQTTMessage):
		siteId = self.Commons.parseSiteId(msg)
		method = constants.EVENT_TOGGLE_FEEDBACK_OFF if msg.topic.lower().endswith('off') else constants.EVENT_TOGGLE_FEEDBACK_ON
		self.broadcast(method=method, exceptions=[self.name], propagateToSkills=True, siteId=siteId)


	def say(self, text, client: str = None, customData: dict = None, canBeEnqueued: bool = True):
		"""
		Initiate a notification session which is termniated once the text is spoken
		:param canBeEnqueued: bool
		:param text: str Text to say
		:param client: int Where to speak
		:param customData: json object
		"""

		client = self.getDefaultSiteId(client)

		if client == constants.ALL or client == constants.RANDOM:
			deviceList = [device.siteId for device in self.getAliceTypeDevices(connectedOnly=True) if device]
			deviceList.append(self.ConfigManager.getAliceConfigByName('deviceName'))

			if client == constants.ALL:
				for device in deviceList:
					device = device.replace(self.DEFAULT_CLIENT_EXTENSION, '')
					if not device:
						continue

					self.say(text=text, client=device, customData=customData)
			else:
				self.say(text=text, client=random.choice(deviceList), customData=customData)
		else:
			if customData is not None:
				if isinstance(customData, dict):
					customData = json.dumps(customData)
				elif not isinstance(customData, str):
					self.logWarning(f'Ask was provided customdata of unsupported type: {customData}')
					customData = ''

			if ' ' in client:
				client = client.replace(' ', '_')

			self._mqttClient.publish(constants.TOPIC_START_SESSION, json.dumps({
				'siteId'    : client,
				'init'      : {
					'type'                   : 'notification',
					'text'                   : text,
					'sendIntentNotRecognized': True,
					'canBeEnqueued'          : canBeEnqueued
				},
				'customData': customData
			}))


	def ask(self, text: str, client: str = None, intentFilter: list = None, customData: dict = None, canBeEnqueued: bool = True, currentDialogState: str = '', probabilityThreshold: float = None):
		"""
		Initiates a new session by asking something and waiting on user answer
		:param probabilityThreshold: The override threshold for the user's answer to this question
		:param currentDialogState: a str representing a state in the dialog, usefull for multiturn dialogs
		:param canBeEnqueued: wheter or not this can be played later if the dialog manager is busy
		:param text: str The text to speak
		:param client: int Where to ask
		:param intentFilter: array Filter to force user intents
		:param customData: json object
		:return:
		"""

		client = self.getDefaultSiteId(client)

		if ' ' in client:
			client = client.replace(' ', '_')

		if customData is not None and not isinstance(customData, dict):
			self.logWarning(f'Ask was provided customdata of unsupported type: {customData}')
			customData = dict()

		user = customData.get('user', constants.UNKNOWN_USER) if customData else constants.UNKNOWN_USER
		session = self.DialogManager.newSession(client, user)

		if currentDialogState:
			session.currentState = currentDialogState

		if probabilityThreshold is not None:
			session.probabilityThreshold = probabilityThreshold

		if client == constants.ALL:
			if not customData:
				customData = '{}'

			customData = json.loads(customData)
			customData['wideAskingSession'] = True

		jsonDict = {
			'siteId': client,
		}

		if customData:
			jsonDict['customData'] = json.dumps(customData)

		initDict = {
			'type'                   : 'action',
			'text'                   : text,
			'canBeEnqueued'          : canBeEnqueued,
			'sendIntentNotRecognized': True
		}

		intentList = list()
		if intentFilter:
			intentList = [x.replace('hermes/intent/', '') if isinstance(x, str) else x.justTopic for x in intentFilter]
			initDict['intentFilter'] = intentList

		jsonDict['init'] = initDict
		session.intentFilter = intentList

		if client == constants.ALL:
			deviceList = self.getAliceTypeDevices(connectedOnly=True)
			deviceList.append(self.ConfigManager.getAliceConfigByName('deviceName'))

			for device in deviceList:
				device = device.replace(self.DEFAULT_CLIENT_EXTENSION, '')
				self.ask(text=text, client=device, intentFilter=intentList, customData=customData)
		else:
			self._mqttClient.publish(constants.TOPIC_START_SESSION, json.dumps(jsonDict))


	def continueDialog(self, sessionId: str, text: str, customData: dict = None, intentFilter: list = None, slot: str = '', currentDialogState: str = '', probabilityThreshold: float = None):
		"""
		Continues a dialog
		:param probabilityThreshold: The probability threshold override for the user's answer to this coming conversation round
		:param currentDialogState: a str representing a state in the dialog, usefull for multiturn dialogs
		:param sessionId: int session id to continue
		:param customData: json str
		:param text: str text spoken
		:param intentFilter: array intent filter for user randomTalk
		:param slot: Optional String, requires intentFilter to contain a single value - If set, the dialogue engine will not run the the intent classification on the user response and go straight to slot filling, assuming the intent is the one passed in the intentFilter, and searching the value of the given slot
		"""

		jsonDict = {
			'sessionId'              : sessionId,
			'text'                   : text,
			'sendIntentNotRecognized': True,
		}

		if customData is not None:
			if isinstance(customData, dict):
				jsonDict['customData'] = json.dumps(customData)
			elif isinstance(customData, str):
				jsonDict['customData'] = customData
			else:
				self.logWarning(f'ContinueDialog was provided customdata of unsupported type: {customData}')
		else:
			customData = dict()

		intentList = list()
		if intentFilter:
			intentList = [x.replace('hermes/intent/', '') if isinstance(x, str) else x.justTopic for x in intentFilter]
			jsonDict['intentFilter'] = intentList

		if slot:
			if intentFilter and len(intentList) > 1:
				self.logWarning('Can\'t specify a slot if you have more than one intent in the intent filter')
			elif not intentFilter:
				self.logWarning('Can\'t use a slot definition without setting an intent filter')
			else:
				jsonDict['slot'] = slot

		session = self.DialogManager.getSession(sessionId=sessionId)
		session.intentFilter = intentList
		if probabilityThreshold is not None:
			session.probabilityThreshold = probabilityThreshold

		if currentDialogState:
			session.currentState = currentDialogState

		session.customData = {**session.customData, **customData}

		self._mqttClient.publish(constants.TOPIC_CONTINUE_SESSION, json.dumps(jsonDict))


	def endDialog(self, sessionId: str = '', text: str = '', client: str = None):
		"""
		Ends a session by speaking the given text
		:param sessionId: int session id to terminate
		:param text: str Text to speak
		:param client: str Where to speak
		"""
		if not sessionId:
			return

		session = self.DialogManager.getSession(sessionId)
		if session and client and text and session.siteId != client:
			self._mqttClient.publish(constants.TOPIC_END_SESSION, json.dumps({
				'sessionId': sessionId
			}))

			self.say(
				text=text,
				client=client
			)
			return


		if text:
			self._mqttClient.publish(constants.TOPIC_END_SESSION, json.dumps({
				'sessionId': sessionId,
				'text'     : text
			}))
		else:
			self._mqttClient.publish(constants.TOPIC_END_SESSION, json.dumps({
				'sessionId': sessionId
			}))


	def endSession(self, sessionId):
		self._mqttClient.publish(constants.TOPIC_END_SESSION, json.dumps({
			'sessionId': sessionId
		}))


	def playSound(self, soundFilename: str, location: Path = None, sessionId: str = '', siteId: str = None, uid: str = '', suffix: str = '.wav'):

		siteId = self.getDefaultSiteId(siteId)

		if not sessionId:
			sessionId = str(uuid.uuid4())

		if not uid:
			uid = str(uuid.uuid4())

		if not location:
			location = Path(self.Commons.rootDir()) / 'system' / 'sounds'
		elif not location.is_absolute():
			location = Path(self.Commons.rootDir()) / location

		if siteId == constants.ALL:
			deviceList = self.getAliceTypeDevices(connectedOnly=True)
			deviceList.append(self.ConfigManager.getAliceConfigByName('deviceName'))

			for device in deviceList:
				device = device.replace(self.DEFAULT_CLIENT_EXTENSION, '')
				self.playSound(soundFilename, location, sessionId, device, uid)
		else:
			if ' ' in siteId:
				siteId = siteId.replace(' ', '_')

			soundFile = Path(location / soundFilename).with_suffix(suffix)

			if not soundFile.exists():
				self.logError(f"Sound file {soundFile} doesn't exist")
				return

			self._mqttClient.publish(constants.TOPIC_PLAY_BYTES.format(siteId).replace('#', uid), payload=bytearray(soundFile.read_bytes()))


	def publish(self, topic: str, payload: (dict, str) = None, stringPayload: str = None, qos: int = 0, retain: bool = False):
		if isinstance(payload, dict):
			payload = json.dumps(payload)

		if stringPayload:
			payload = stringPayload

		if payload and not isinstance(payload, str) and not isinstance(payload, bytearray) and not isinstance(payload, int) and not isinstance(payload, float):
			self.logWarning(f'Trying to send an invalid payload: {payload}')
			return

		self._mqttClient.publish(topic, payload, qos, retain)


	def mqttBroadcast(self, topic: str, payload: dict = None, qos: int = 0, retain: bool = False, deviceType: str = 'AliceSatellite'):
		if not payload:
			payload = dict()

		for device in self.DeviceManager.getDevicesByType(deviceType=deviceType):
			payload['siteId'] = device.siteId
			self.publish(topic=topic, payload=payload, qos=qos, retain=retain)

		payload['siteId'] = self.ConfigManager.getAliceConfigByName('deviceName')
		self.publish(topic=topic, payload=json.dumps(payload), qos=qos, retain=retain)


	def configureIntents(self, intents: list):
		# Keep a track of the deactivated intents to make use of alternatives
		for intent in intents:
			if intent['enable'] and intent['intentId'] in self._deactivatedIntents:
				self._deactivatedIntents.remove(intent['intentId'])
			elif not intent['enable'] and intent['intentId'] not in self._deactivatedIntents:
				self._deactivatedIntents.append(intent['intentId'])

		self.publish(
			topic=constants.TOPIC_DIALOGUE_MANAGER_CONFIGURE,
			payload={
				'intents': intents
			}
		)
		self.broadcast(method=constants.EVENT_CONFIGURE_INTENT, exceptions=[self.name], propagateToSkills=True, intents=intents)


	@property
	def mqttClient(self) -> mqtt.Client:
		return self._mqttClient


	def toggleFeedbackSounds(self, state='On'):
		"""
		Activates or disables the feedback sounds, on all devices
		:param state: str On or off
		"""

		deviceList = [device.name.replace(self.DEFAULT_CLIENT_EXTENSION, '') for device in self.DeviceManager.getDevicesByType(deviceType=self.DeviceManager.SAT_TYPE, connectedOnly=True)]
		deviceList.append(self.ConfigManager.getAliceConfigByName('deviceName'))

		for siteId in deviceList:
			publish.single(constants.TOPIC_TOGGLE_FEEDBACK.format(state.title()), payload=json.dumps({'siteId': siteId}))


	def getDefaultSiteId(self, siteId: str = None) -> str:
		return self.ConfigManager.getAliceConfigByName('deviceName') if not siteId else siteId


	def getAliceTypeDevices(self, connectedOnly: bool = False) -> List[Device]:
		#todo remove hard coded AliceSatellite. replace for example with some type of "device ability" -> "can broadcast" -> "can play sound" ..
		return self.DeviceManager.getDevicesByType(deviceType=self.DeviceManager.SAT_TYPE, connectedOnly=connectedOnly)
