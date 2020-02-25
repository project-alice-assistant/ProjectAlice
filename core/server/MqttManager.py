import json
import uuid
from pathlib import Path

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import random
import re

from core.ProjectAliceExceptions import AccessLevelTooLow
from core.base.model.Intent import Intent
from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.util.Decorators import deprecated


class MqttManager(Manager):

	def __init__(self):
		super().__init__()

		self._mqttClient = mqtt.Client()
		self._thanked = False
		self._wideAskingSessions = list()
		self._multiDetectionsHolder = list()

		self._audioFrameRegex = re.compile(constants.TOPIC_AUDIO_FRAME.replace('{}', '(.*)'))
		self._wakewordDetectedRegex = re.compile(constants.TOPIC_WAKEWORD_DETECTED.replace('{}', '(.*)'))
		self._vadUpRegex = re.compile(constants.TOPIC_VAD_UP.replace('{}', '(.*)'))
		self._vadDownRegex = re.compile(constants.TOPIC_VAD_DOWN.replace('{}', '(.*)'))


	# noinspection PyUnusedLocal
	def onLog(self, client, userdata, level, buf):
		if level != 16:
			self.logError(buf)


	def onStart(self):
		super().onStart()

		self._mqttClient.on_message = self.onMqttMessage
		self._mqttClient.on_connect = self.onConnect
		self._mqttClient.on_log = self.onLog

		self._mqttClient.message_callback_add(constants.TOPIC_HOTWORD_DETECTED, self.onHotwordDetected)
		for username in self.UserManager.getAllUserNames():
			self._mqttClient.message_callback_add(constants.TOPIC_WAKEWORD_DETECTED.replace('{user}', username), self.onHotwordDetected)

		self._mqttClient.message_callback_add(constants.TOPIC_SESSION_STARTED, self.onSnipsSessionStarted)

		self._mqttClient.message_callback_add(constants.TOPIC_ASR_START_LISTENING, self.onSnipsStartListening)

		self._mqttClient.message_callback_add(constants.TOPIC_ASR_STOP_LISTENING, self.onSnipsStopListening)

		self._mqttClient.message_callback_add(constants.TOPIC_INTENT_PARSED, self.onSnipsIntentParsed)

		self._mqttClient.message_callback_add(constants.TOPIC_TEXT_CAPTURED, self.onSnipsCaptured)

		self._mqttClient.message_callback_add(constants.TOPIC_TTS_SAY, self.onSnipsSay)

		self._mqttClient.message_callback_add(constants.TOPIC_TTS_FINISHED, self.onSnipsSayFinished)

		self._mqttClient.message_callback_add(constants.TOPIC_SESSION_ENDED, self.onSnipsSessionEnded)

		self._mqttClient.message_callback_add(constants.TOPIC_INTENT_NOT_RECOGNIZED, self.onSnipsIntentNotRecognized)

		self._mqttClient.message_callback_add(constants.TOPIC_SESSION_QUEUED, self.onSnipsSessionQueued)

		self._mqttClient.message_callback_add(constants.TOPIC_NLU_QUERY, self.onTopicNluQuery)

		self._mqttClient.message_callback_add(constants.TOPIC_PARTIAL_TEXT_CAPTURED, self.onNluPartialCapture)

		self.connect()


	def onStop(self):
		super().onStop()
		self.disconnect()


	# noinspection PyUnusedLocal
	def onConnect(self, client, userdata, flags, rc):

		subscribedEvents = [
			(constants.TOPIC_SESSION_ENDED, 0),
			(constants.TOPIC_SESSION_STARTED, 0),
			(constants.TOPIC_HOTWORD_DETECTED, 0),
			(constants.TOPIC_INTENT_NOT_RECOGNIZED, 0),
			(constants.TOPIC_INTENT_PARSED, 0),
			(constants.TOPIC_TTS_FINISHED, 0),
			(constants.TOPIC_ASR_START_LISTENING, 0),
			(constants.TOPIC_TTS_SAY, 0),
			(constants.TOPIC_TEXT_CAPTURED, 0),
			(constants.TOPIC_HOTWORD_TOGGLE_ON, 0),
			(constants.TOPIC_NLU_QUERY, 0)
		]

		for username in self.UserManager.getAllUserNames():
			subscribedEvents.append((constants.TOPIC_WAKEWORD_DETECTED.format(username), 0))

		subscribedEvents.append((constants.TOPIC_VAD_UP.format('default'), 0))
		subscribedEvents.append((constants.TOPIC_VAD_DOWN.format('default'), 0))
		for device in self.DeviceManager.getDevicesByType('alicesatellite'):
			subscribedEvents.append((constants.TOPIC_VAD_UP.format(device.room), 0))
			subscribedEvents.append((constants.TOPIC_VAD_DOWN.format(device.room), 0))

		self._mqttClient.subscribe(subscribedEvents)
		self.subscribeSkillIntents()
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


	def subscribeSkillIntents(self, skillName: str = None):
		if skillName:
			self.SkillManager.getSkillInstance(skillName).subscribe(self._mqttClient)
			return

		for skill in self.SkillManager.activeSkills.values():
			skill.subscribe(self._mqttClient)


	# noinspection PyUnusedLocal
	def onMqttMessage(self, client, userdata, message: mqtt.MQTTMessage):
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

			siteId = self.Commons.parseSiteId(message)
			payload = self.Commons.payload(message)
			sessionId = self.Commons.parseSessionId(message)

			session = self.DialogSessionManager.getSession(sessionId)
			if session:
				session.update(message)
				if self.MultiIntentManager.processMessage(message):
					return

			if message.topic == constants.TOPIC_TEXT_CAPTURED and session:
				return

			elif message.topic == constants.TOPIC_HOTWORD_TOGGLE_ON:
				self.broadcast(method=constants.EVENT_HOTWORD_TOGGLE_ON, exceptions=[constants.DUMMY], siteId=siteId)
				return

			if not session:  # It is a device trying to communicate with Alice
				session = self.DeviceManager.deviceMessage(message)
				self.broadcast(method=constants.EVENT_MESSAGE, exceptions=[self.name], session=session)
				self.SkillManager.skillBroadcast(method='dispatchMessage', session=session)
				return

			redQueen = self.SkillManager.getSkillInstance('RedQueen')
			if redQueen and not redQueen.inTheMood(session):
				return

			if 'intent' in payload and payload['intent']['confidenceScore'] < self.ConfigManager.getAliceConfigByName('probabilityThreshold'):
				if session.notUnderstood < self.ConfigManager.getAliceConfigByName('notUnderstoodRetries'):
					session.notUnderstood = session.notUnderstood + 1

					self.continueDialog(
						sessionId=sessionId,
						text=self.TalkManager.randomTalk('notUnderstood', skill='system')
					)
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

			for skill in self.SkillManager.activeSkills.values():
				try:
					consumed = skill.onDispatchMessage(session)
				except AccessLevelTooLow:
					# The command was recognized but required higher access level
					return

				# Authentication might end the session directly from a skill
				# if not self.DialogSessionManager.getSession(sessionId):
				# 	return

				if self.MultiIntentManager.isProcessing(sessionId):
					self.MultiIntentManager.processNextIntent(sessionId)
					return

				elif consumed or consumed is None:
					self.logInfo(f"The intent {message.topic.replace('hermes/intent/', '')} was consumed by {skill.__class__.__name__}")
					return

			self.logWarning(f"Intent \"{message.topic}\" wasn't consumed by any skill")
			if session.notUnderstood < self.ConfigManager.getAliceConfigByName('notUnderstoodRetries'):
				session.notUnderstood = session.notUnderstood + 1

				self.continueDialog(
					sessionId=sessionId,
					text=self.TalkManager.randomTalk('notUnderstood', skill='system')
				)
				return
			else:
				session.notUnderstood = 0
				self.endDialog(
					sessionId=sessionId,
					text=self.TalkManager.randomTalk('notUnderstoodEnd', skill='system')
				)
			return

		except Exception as e:
			self.logError(f'Error in onMessage: {e}')


	# noinspection PyUnusedLocal
	def onHotwordDetected(self, client, data, msg):
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

		self.DialogSessionManager.preSession(siteId, user)

		if user == constants.UNKNOWN_USER:
			self.broadcast(method=constants.EVENT_HOTWORD, exceptions=[self.name], propagateToSkills=True, siteId=siteId, user=user)
		else:
			self.broadcast(method=constants.EVENT_WAKEWORD, exceptions=[self.name], propagateToSkills=True, siteId=siteId, user=user)


	def handleMultiDetection(self):
		if len(self._multiDetectionsHolder) <= 1:
			self._multiDetectionsHolder = list()
			return

		sessions = self.DialogSessionManager.sessions
		for sessionId in sessions:
			payload = self.Commons.payload(sessions[sessionId].message)
			if payload['siteId'] != self._multiDetectionsHolder[0]:
				self.endSession(sessionId=sessionId)

		self._multiDetectionsHolder = list()


	# noinspection PyUnusedLocal
	def onSnipsSessionStarted(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogSessionManager.addSession(sessionId=sessionId, message=msg)

		if session:
			self.broadcast(method=constants.EVENT_SESSION_STARTED, exceptions=[self.name], propagateToSkills=True, session=session)


	# noinspection PyUnusedLocal
	def onSnipsSessionQueued(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogSessionManager.addSession(sessionId=sessionId, message=msg)

		if session:
			self.broadcast(method=constants.EVENT_SESSION_QUEUED, exceptions=[self.name], propagateToSkills=True, session=session)


	# noinspection PyUnusedLocal
	def onTopicNluQuery(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)

		session = self.DialogSessionManager.getSession(sessionId)
		if not session:
			session = self.DialogSessionManager.addSession(sessionId=sessionId, message=msg)

		self.broadcast(method=constants.EVENT_NLU_QUERY, exceptions=[self.name], propagateToSkills=True, session=session)


	# noinspection PyUnusedLocal
	def onSnipsStartListening(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogSessionManager.getSession(sessionId=sessionId)

		if session:
			self.broadcast(method=constants.EVENT_START_LISTENING, exceptions=[self.name], propagateToSkills=True, session=session)


	# noinspection PyUnusedLocal
	def onSnipsStopListening(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogSessionManager.getSession(sessionId=sessionId)

		if session:
			self.broadcast(method=constants.EVENT_STOP_LISTENING, exceptions=[self.name], propagateToSkills=True, session=session)


	# noinspection PyUnusedLocal
	def onSnipsCaptured(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogSessionManager.getSession(sessionId=sessionId)

		if session:
			self.broadcast(method=constants.EVENT_CAPTURED, exceptions=[self.name], propagateToSkills=True, session=session)


	def onSnipsIntentParsed(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogSessionManager.getSession(sessionId=sessionId)

		if session:
			session.update(msg)
			self.broadcast(method=constants.EVENT_INTENT_PARSED, exceptions=[self.name], propagateToSkills=True, session=session)

			if session.isAPIGenerated:
				intent = Intent(session.payload['intent']['intentName'])
				message = mqtt.MQTTMessage(topic=str.encode(str(intent)))
				message.payload = json.dumps(session.payload)
				self.onMqttMessage(client=client, userdata=data, message=message)


	# noinspection PyUnusedLocal
	def onSnipsSessionEnded(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogSessionManager.getSession(sessionId)

		if session:
			session.update(msg)
		else:
			self.broadcast(method=constants.EVENT_SESSION_ENDED, exceptions=[self.name])
			return

		reason = session.payload['termination']['reason']
		if reason:
			if reason == 'abortedByUser':
				self.broadcast(method=constants.EVENT_USER_CANCEL, exceptions=[self.name], propagateToSkills=True, session=session)
			elif reason == 'timeout':
				self.broadcast(method=constants.EVENT_SESSION_TIMEOUT, exceptions=[self.name], propagateToSkills=True, session=session)
			elif reason == 'intentNotRecognized':
				# This should never trigger, as "sendIntentNotRecognized" is always set to True, but we never know
				self.onSnipsIntentNotRecognized(None, data, msg)
			elif reason == 'error':
				self.broadcast(method=constants.EVENT_SESSION_ERROR, exceptions=[self.name], propagateToSkills=True, session=session)
			else:
				self.broadcast(method=constants.EVENT_SESSION_ENDED, exceptions=[self.name], propagateToSkills=True, session=session)

		self.broadcast(method=constants.EVENT_SESSION_ENDED, exceptions=[self.name], propagateToSkills=True, session=session)
		self.DialogSessionManager.removeSession(sessionId=sessionId)


	# noinspection PyUnusedLocal
	def onSnipsSay(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		payload = self.Commons.payload(msg)

		session = self.DialogSessionManager.getSession(sessionId)
		if session:
			session.payload = payload
			siteId = session.siteId
		else:
			siteId = self.Commons.parseSiteId(msg)

		if 'text' in payload:
			skill = self.SkillManager.getSkillInstance('ContextSensitive')
			if skill:
				skill.addChat(text=payload['text'], siteId=siteId)

		self.broadcast(method=constants.EVENT_SAY, exceptions=[self.name], propagateToSkills=True, session=session)


	# noinspection PyUnusedLocal
	def onSnipsSayFinished(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		payload = self.Commons.payload(msg)

		session = self.DialogSessionManager.getSession(sessionId)
		if session:
			session.payload = payload

		self.broadcast(method=constants.EVENT_SAY_FINISHED, exceptions=[self.name], propagateToSkills=True, session=session)


	# noinspection PyUnusedLocal
	def onSnipsIntentNotRecognized(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogSessionManager.getSession(sessionId)

		if not session:
			self.ask(text=self.TalkManager.randomTalk('notUnderstood', skill='system'), client='default')
		else:
			if msg.topic == Intent('UserRandomAnswer'):
				return

			if session.customData and 'skill' in session.customData and 'RandomWord' in session.slots:
				skill = self.SkillManager.getSkillInstance(session.customData['skill'])
				if skill:
					skill.onMessage(Intent('UserRandomAnswer'), session)
					return

			if session.notUnderstood < self.ConfigManager.getAliceConfigByName('notUnderstoodRetries'):
				session.notUnderstood = session.notUnderstood + 1
				self.reviveSession(session, self.TalkManager.randomTalk('notUnderstood', skill='system'))
			else:
				session.notUnderstood = 0
				self.endDialog(sessionId=sessionId, text=self.TalkManager.randomTalk('notUnderstoodEnd', skill='system'))

		self.broadcast(method=constants.EVENT_INTENT_NOT_RECOGNIZED, exceptions=[self.name], propagateToSkills=True, session=session)


	def onNluPartialCapture(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = self.Commons.parseSessionId(msg)
		session = self.DialogSessionManager.getSession(sessionId)

		if session:
			payload = self.Commons.payload(msg)
			self.broadcast(method=constants.EVENT_PARTIAL_TEXT_CAPTURED, exceptions=[self.name], propagateToSkills=True, session=session, text=payload['text'], likelihood=payload['likelihood'], seconds=payload['seconds'])


	def reviveSession(self, session: DialogSession, text: str):
		self.endSession(session.sessionId)
		self.DialogSessionManager.planSessionRevival(session)
		previousIntent = session.previousIntent[-1] if session.previousIntent else None
		self.ask(text=text, customData=session.customData, previousIntent=previousIntent, intentFilter=session.intentFilter, client=session.siteId)


	def say(self, text, client: str = constants.DEFAULT_SITE_ID, customData: dict = None, canBeEnqueued: bool = True):
		"""
		Initiate a notification session which is termniated once the text is spoken
		:param canBeEnqueued: bool
		:param text: str Text to say
		:param client: int Where to speak
		:param customData: json object
		"""

		if client == constants.ALL or client == constants.RANDOM:
			deviceList = [device.room for device in self.DeviceManager.getDevicesByType('AliceSatellite', connectedOnly=True) if device]
			deviceList.append(constants.DEFAULT_SITE_ID)

			if client == constants.ALL:
				for device in deviceList:
					device = device.replace('@mqtt', '')
					if not device:
						continue

					self.say(text=text, client=device, customData=customData)
			else:
				self.say(text=text, client=random.choice(deviceList), customData=customData)
		else:
			if customData is not None:
				if isinstance(customData, dict):
					customData = json.dumps(customData)
				elif isinstance(customData, str):
					pass
				else:
					self.logWarning(f'Ask was provided customdata of unsupported type: {customData}')
					customData = ''

			if ' ' in client:
				client = client.replace(' ', '_')

			if self.ConfigManager.getAliceConfigByName('outputOnSonos') != '1' or (self.ConfigManager.getAliceConfigByName('outputOnSonos') == '1' and self.SkillManager.getSkillInstance('Sonos') is None or not self.SkillManager.getSkillInstance('Sonos').anySkillHere(client)) or not self.SkillManager.getSkillInstance('Sonos').active:
				self._mqttClient.publish(constants.TOPIC_START_SESSION, json.dumps({
					'siteId': client,
					'init': {
						'type': 'notification',
						'text': text,
						'sendIntentNotRecognized': True,
						'canBeEnqueued': canBeEnqueued
					},
					'customData': customData
				}))
			else:
				self._speakOnSonos(text, client)
				self._mqttClient.publish(constants.TOPIC_START_SESSION, json.dumps({
					'siteId': client,
					'init': {
						'type': 'notification',
						'sendIntentNotRecognized': True
					},
					'customData': customData
				}))


	def ask(self, text: str, client: str = constants.DEFAULT_SITE_ID, intentFilter: list = None, customData: dict = None, previousIntent: str = '', canBeEnqueued: bool = True, currentDialogState: str = ''):
		"""
		Initiates a new session by asking something and waiting on user answer
		:param currentDialogState: a str representing a state in the dialog, usefull for multiturn dialogs
		:param canBeEnqueued: wheter or not this can be played later if the dialog manager is busy
		:param previousIntent: the previous intent that triggered the method, if available
		:param text: str The text to speak
		:param client: int Where to ask
		:param intentFilter: array Filter to force user intents
		:param customData: json object
		:return:
		"""

		if ' ' in client:
			client = client.replace(' ', '_')

		if customData is not None and not isinstance(customData, dict):
			self.logWarning(f'Ask was provided customdata of unsupported type: {customData}')
			customData = dict()

		user = customData.get('user', constants.UNKNOWN_USER) if customData else constants.UNKNOWN_USER
		preSession = self.DialogSessionManager.preSession(client, user)
		if previousIntent:
			preSession.intentHistory.append(previousIntent)

		preSession.intentFilter = intentFilter

		if currentDialogState:
			preSession.currentState = currentDialogState

		if client == constants.ALL:
			if not customData:
				customData = dict()

			customData = json.loads(customData)
			customData['wideAskingSession'] = True

		jsonDict = {
			'siteId': client,
		}

		if customData:
			jsonDict['customData'] = json.dumps(customData)

		initDict = {
			'type': 'action',
			'text': text,
			'canBeEnqueued': canBeEnqueued,
			'sendIntentNotRecognized': True
		}

		if intentFilter:
			intentList = [str(x).replace('hermes/intent/', '') for x in intentFilter]
			initDict['intentFilter'] = intentList

		jsonDict['init'] = initDict

		if self.ConfigManager.getAliceConfigByName('outputOnSonos') != '1' or (self.ConfigManager.getAliceConfigByName('outputOnSonos') == '1' or self.SkillManager.getSkillInstance('Sonos') is None and not self.SkillManager.getSkillInstance('Sonos').anySkillHere(client)) or not self.SkillManager.getSkillInstance('Sonos').active:
			if client == constants.ALL:
				deviceList = self.DeviceManager.getDevicesByType('AliceSatellite', connectedOnly=True)
				deviceList.append(constants.DEFAULT_SITE_ID)

				for device in deviceList:
					device = device.replace('@mqtt', '')
					self.ask(text=text, client=device, intentFilter=intentFilter, customData=customData)
			else:
				self._mqttClient.publish(constants.TOPIC_START_SESSION, json.dumps(jsonDict))
		else:
			jsonDict['init']['text'] = ''
			self._mqttClient.publish(constants.TOPIC_START_SESSION, json.dumps(jsonDict))

			self._speakOnSonos(text, client)


	def continueDialog(self, sessionId: str, text: str, customData: dict = None, intentFilter: list = None, previousIntent: str = '', slot: str = '', currentDialogState: str = ''):
		"""
		Continues a dialog
		:param currentDialogState: a str representing a state in the dialog, usefull for multiturn dialogs
		:param sessionId: int session id to continue
		:param customData: json str
		:param text: str text spoken
		:param intentFilter: array intent filter for user randomTalk
		:param previousIntent: the previous intent that started the dialog continuation
		:param slot: Optional String, requires intentFilter to contain a single value - If set, the dialogue engine will not run the the intent classification on the user response and go straight to slot filling, assuming the intent is the one passed in the intentFilter, and searching the value of the given slot
		"""

		if previousIntent:
			self.DialogSessionManager.addPreviousIntent(sessionId=sessionId, previousIntent=previousIntent)

		jsonDict = {
			'sessionId': sessionId,
			'text': text,
			'sendIntentNotRecognized': True,
		}

		if customData is not None:
			if isinstance(customData, dict):
				jsonDict['customData'] = json.dumps(customData)
			elif isinstance(customData, str):
				jsonDict['customData'] = customData
			else:
				self.logWarning(f'ContinueDialog was provided customdata of unsupported type: {customData}')

		intentList = list()
		if intentFilter:
			intentList = [str(x).replace('hermes/intent/', '') for x in intentFilter]
			jsonDict['intentFilter'] = intentList

		if slot:
			if intentFilter and len(intentList) > 1:
				self.logWarning('Can\'t specify a slot if you have more than one intent in the intent filter')
			elif not intentFilter:
				self.logWarning('Can\'t use a slot definition without setting an intent filter')
			else:
				jsonDict['slot'] = slot

		session = self.DialogSessionManager.getSession(sessionId=sessionId)
		session.intentFilter = intentFilter

		if currentDialogState:
			session.currentState = currentDialogState

		if self.ConfigManager.getAliceConfigByName('outputOnSonos') != '1' or (self.ConfigManager.getAliceConfigByName('outputOnSonos') == '1' and self.SkillManager.getSkillInstance('Sonos') is None or not self.SkillManager.getSkillInstance('Sonos').anySkillHere(session.siteId)) or not self.SkillManager.getSkillInstance('Sonos').active:
			self._mqttClient.publish(constants.TOPIC_CONTINUE_SESSION, json.dumps(jsonDict))
		else:
			jsonDict['text'] = ''
			self._mqttClient.publish(constants.TOPIC_CONTINUE_SESSION, json.dumps(jsonDict))
			self._speakOnSonos(text, constants.DEFAULT_SITE_ID)


	@deprecated
	def endTalk(self, sessionId: str = '', text: str = '', client: str = ''):
		return self.endDialog(sessionId, text, client)


	def endDialog(self, sessionId: str = '', text: str = '', client: str = ''):
		"""
		Ends a session by speaking the given text
		:param sessionId: int session id to terminate
		:param text: str Text to speak
		:param client: int Where to speak
		"""
		if not sessionId:
			return

		session = self.DialogSessionManager.getSession(sessionId)
		if session and session.isAPIGenerated:
			return self.say(text=text, client=session.siteId)

		client = client.replace(' ', '_')

		if self.ConfigManager.getAliceConfigByName('outputOnSonos') != '1' or (self.ConfigManager.getAliceConfigByName('outputOnSonos') == '1' and self.SkillManager.getSkillInstance('Sonos') is None or not self.SkillManager.getSkillInstance('Sonos').anySkillHere(client)) or not self.SkillManager.getSkillInstance('Sonos').active:
			if text:
				self._mqttClient.publish(constants.TOPIC_END_SESSION, json.dumps({
					'sessionId': sessionId,
					'text'     : text
				}))
			else:
				self._mqttClient.publish(constants.TOPIC_END_SESSION, json.dumps({
					'sessionId': sessionId
				}))
		else:
			self._mqttClient.publish(constants.TOPIC_END_SESSION, json.dumps({
				'sessionId': sessionId
			}))
			if text:
				self._speakOnSonos(text, client)


	def endSession(self, sessionId):
		self._mqttClient.publish(constants.TOPIC_END_SESSION, json.dumps({
			'sessionId': sessionId
		}))


	def partialTextCaptured(self, session: DialogSession, text: str, likelihood: float, seconds: float):
		self._mqttClient.publish(constants.TOPIC_PARTIAL_TEXT_CAPTURED, json.dumps({
			'text': text,
			'likelihood': likelihood,
			'seconds': seconds,
			'siteId': session.siteId,
			'sessionId': session.sessionId
		}))


	def playSound(self, soundFilename: str, location: Path = None, sessionId: str = '', siteId: str = constants.DEFAULT_SITE_ID, uid: str = '', suffix: str = '.wav'):

		if not sessionId:
			sessionId = str(uuid.uuid4())

		if not uid:
			uid = str(uuid.uuid4())

		if not location:
			location = Path(self.Commons.rootDir()) / 'system' / 'sounds'
		elif not location.is_absolute():
			location = Path(self.Commons.rootDir()) / location

		if siteId == constants.ALL:
			deviceList = self.DeviceManager.getDevicesByType('AliceSatellite', connectedOnly=True)
			deviceList.append(constants.DEFAULT_SITE_ID)

			for device in deviceList:
				device = device.replace('@mqtt', '')
				self.playSound(soundFilename, location, sessionId, device, uid)
		else:
			if ' ' in siteId:
				siteId = siteId.replace(' ', '_')

			soundFile = Path(location / soundFilename).with_suffix(suffix)

			if not soundFile.exists():
				self.logError(f"Sound file {soundFile} doesn't exist")
				return

			self._mqttClient.publish(constants.TOPIC_PLAY_BYTES.format(siteId, uid), payload=bytearray(soundFile.read_bytes()))


	def publish(self, topic: str, payload: (dict, str) = None, qos: int = 0, retain: bool = False):
		if isinstance(payload, dict):
			payload = json.dumps(payload)

		self._mqttClient.publish(topic, payload, qos, retain)


	def mqttBroadcast(self, topic: str, payload: dict = None, qos: int = 0, retain: bool = False, deviceType: str = 'AliceSatellite'):
		if not payload:
			payload = dict()

		for device in self.DeviceManager.getDevicesByType(deviceType):
			payload['siteId'] = device.room
			self.publish(topic=topic, payload=payload, qos=qos, retain=retain)

		payload['siteId'] = constants.DEFAULT_SITE_ID
		self.publish(topic=topic, payload=json.dumps(payload), qos=qos, retain=retain)


	def configureIntents(self, intents: list):
		self.publish(
			topic=constants.TOPIC_DIALOGUE_MANAGER_CONFIGURE,
			payload={
				'intents': intents
			}
		)


	@property
	def mqttClient(self) -> mqtt.Client:
		return self._mqttClient


	@deprecated
	def _speakOnSonos(self, text, client):
		if text == '':
			return

		self.Commons.runRootSystemCommand([
			Path(self.Commons.rootDir(), '/system/scripts/snipsSuperTTS.sh'),
			Path('/share/tmp.wav'), 'amazon', self.LanguageManager.activeLanguage, 'US', 'Joanna', 'FEMALE', text, '22050'
		])

		sonosSkill = self.SkillManager.getSkillInstance('Sonos')
		if sonosSkill:
			sonosSkill.aliceSpeak(client)
		else:
			self.logError('Tried to speak on Sonos but Sonos skill is disabled or missing')


	def toggleFeedbackSounds(self, state='On'):
		"""
		Activates or disables the feedback sounds, on all devices
		:param state: str On or off
		"""

		deviceList = self.DeviceManager.getDevicesByType('AliceSatellite', connectedOnly=True)
		deviceList.append(constants.DEFAULT_SITE_ID)

		for device in deviceList:
			device = device.replace('@mqtt', '')
			publish.single(constants.TOPIC_TOGGLE_FEEDBACK.format(state.title()), payload=json.dumps({'siteId': device}))
