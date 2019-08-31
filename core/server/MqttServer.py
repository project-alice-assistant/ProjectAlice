# -*- coding: utf-8 -*-

import json
import subprocess
import uuid

import os
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

import core.base.Managers as managers
from core.ProjectAliceExceptions import AccessLevelTooLow
from core.base.Manager import Manager
from core.base.model.Intent import Intent
from core.commons import commons
from core.commons.commons import deprecated
from core.dialog.model.DialogSession import DialogSession


class MqttServer(Manager):
	NAME = 'MqttServer'

	_HERMES_DEFAULT_HOTWORD_DETECTED = 'hermes/hotword/default/detected'
	_HERMES_HOTWORD_USER_DETECTED = 'hermes/hotword/{user}/detected'

	_HERMES_START_LISTENING = 'hermes/asr/startListening'

	_HERMES_SESSION_STARTED = 'hermes/dialogueManager/sessionStarted'
	_HERMES_SESSION_QUEUED = 'hermes/dialogueManager/sessionQueued'
	_HERMES_SESSION_ENDED = 'hermes/dialogueManager/sessionEnded'

	_HERMES_CAPTURED = 'hermes/asr/textCaptured'

	_HERMES_NOT_RECOGNIZED = 'hermes/dialogueManager/intentNotRecognized'
	_HERMES_INTENT_PARSED = 'hermes/nlu/intentParsed'

	_HERMES_SAY = 'hermes/tts/say'
	_HERMES_SAY_FINISHED = 'hermes/tts/sayFinished'

	_HERMES_HOTWORD_TOGGLE_ON = 'hermes/hotword/toggleOn'


	def __init__(self, mainClass):
		super().__init__(mainClass, self.NAME)

		managers.MqttServer = self

		self._mqttClient = mqtt.Client()
		self._thanked = False
		self._wideAskingSessions = list()
		self._multiDetectionsHolder = list()


	# noinspection PyUnusedLocal
	def onLog(self, client, userdata, level, buf):
		if level != 16:
			self._logger.error(buf)


	def onStart(self):
		super().onStart()

		self._mqttClient.on_message = self.onMessage
		self._mqttClient.on_connect = self.onConnect
		self._mqttClient.on_log = self.onLog

		self._mqttClient.message_callback_add(self._HERMES_DEFAULT_HOTWORD_DETECTED, self.onHotwordDetected)
		for username in managers.UserManager.getAllUserNames():
			self._mqttClient.message_callback_add(self._HERMES_HOTWORD_USER_DETECTED.replace('{user}', username), self.onHotwordDetected)

		self._mqttClient.message_callback_add(self._HERMES_SESSION_STARTED, self.onSnipsSessionStarted)

		self._mqttClient.message_callback_add(self._HERMES_START_LISTENING, self.onSnipsStartListening)

		self._mqttClient.message_callback_add(self._HERMES_INTENT_PARSED, self.onSnipsIntentParsed)

		self._mqttClient.message_callback_add(self._HERMES_CAPTURED, self.onSnipsCaptured)

		self._mqttClient.message_callback_add(self._HERMES_SAY, self.onSnipsSay)

		self._mqttClient.message_callback_add(self._HERMES_SAY_FINISHED, self.onSnipsSayFinished)

		self._mqttClient.message_callback_add(self._HERMES_SESSION_ENDED, self.onSnipsSessionEnded)

		self._mqttClient.message_callback_add(self._HERMES_NOT_RECOGNIZED, self.onSnipsIntentNotRecognized)

		self._mqttClient.message_callback_add(self._HERMES_SESSION_QUEUED, self.onSnipsSessionQueued)

		self._mqttClient.connect(managers.ConfigManager.getAliceConfigByName('mqttHost'), int(managers.ConfigManager.getAliceConfigByName('mqttPort')))

		self._mqttClient.loop_start()
		self._logger.info('Started {}'.format(self.NAME))


	def onStop(self):
		super().onStop()
		self._mqttClient.loop_stop()
		self._mqttClient.disconnect()


	# noinspection PyUnusedLocal
	def onConnect(self, client, userdata, flags, rc):

		subscribedEvents = [
			(self._HERMES_SESSION_ENDED, 0),
			(self._HERMES_SESSION_STARTED, 0),
			(self._HERMES_DEFAULT_HOTWORD_DETECTED, 0),
			(self._HERMES_NOT_RECOGNIZED, 0),
			(self._HERMES_INTENT_PARSED, 0),
			(self._HERMES_SAY_FINISHED, 0),
			(self._HERMES_START_LISTENING, 0),
			(self._HERMES_SAY, 0),
			(self._HERMES_CAPTURED, 0),
			(self._HERMES_HOTWORD_TOGGLE_ON, 0)
		]

		for username in managers.UserManager.getAllUserNames():
			subscribedEvents.append((self._HERMES_HOTWORD_USER_DETECTED.replace('{user}', username), 0))

		self._mqttClient.subscribe(subscribedEvents)
		self.subscribeModuleIntents()
		self.toggleFeedbackSounds()


	def subscribeModuleIntents(self, moduleName: str = None):
		if moduleName:
			managers.ModuleManager.getModuleInstance(moduleName).subscribe(self._mqttClient)
			return

		for module in managers.ModuleManager.getModules().copy().values():
			module['instance'].subscribe(self._mqttClient)


	# noinspection PyUnusedLocal
	def onMessage(self, client, userdata, message: mqtt.MQTTMessage):
		if message.topic == self._HERMES_INTENT_PARSED:
			return

		siteId = commons.parseSiteId(message)
		payload = commons.payload(message)
		sessionId = commons.parseSessionId(message)

		session = managers.DialogSessionManager.getSession(sessionId)
		if session:
			session.update(message)
			if managers.MultiIntentManager.processMessage(message):
				return

		if message.topic == self._HERMES_CAPTURED:
			managers.ModuleManager.broadcast('onASRCaptured', args=[payload])
			return

		elif message.topic == self._HERMES_START_LISTENING:
			managers.ModuleManager.broadcast('onListening', args=[siteId])
			return

		elif message.topic == self._HERMES_HOTWORD_TOGGLE_ON:
			managers.ModuleManager.broadcast('onHotwordToggleOn', args=[siteId])
			return

		session = managers.DialogSessionManager.getSession(sessionId)
		if not session:
			session = managers.DeviceManager.onMessage(message)
			if not session:
				self._logger.warning('[{}] Got a message on ({}) but nobody knows what to do with it'.format(self.name, message.topic))
				self.endTalk(sessionId)
				return

		redQueen = managers.ModuleManager.getModuleInstance('RedQueen')
		if redQueen and not redQueen.inTheMood(session):
			return

		customData = session.customData
		if 'intent' in payload and payload['intent']['confidenceScore'] < managers.ConfigManager.getAliceConfigByName('probabilityTreshold'):
			self.continueDialog(
				sessionId=sessionId,
				text=managers.TalkManager.randomTalk('notUnderstood', module='system')
			)
			return

		moduleManager = managers.ModuleManager
		module = moduleManager.getModuleInstance('ContextSensitive')
		if module:
			module.addToMessageHistory(session)

		modules = moduleManager.getModules()
		for key, modul in modules.items():
			module = modul['instance']
			print('called {}'.format(modul['instance'].name))
			try:
				consumed = module.onMessage(message.topic, session)
			except AccessLevelTooLow:
				# The command was recognized but required higher access level
				return

			# Authentication might end the session directly from a module
			if not managers.DialogSessionManager.getSession(sessionId):
				return

			if managers.MultiIntentManager.isProcessing(sessionId):
				managers.MultiIntentManager.processNextIntent(sessionId)
				return

			elif consumed:
				return

		self._logger.warning("[{}] Intent \"{}\" wasn't consumed by any module".format(self.name, message.topic))
		self.endTalk(sessionId)


	# noinspection PyUnusedLocal
	def onHotwordDetected(self, client, data, msg):
		siteId = commons.parseSiteId(msg)
		payload = commons.payload(msg)

		if len(self._multiDetectionsHolder) == 0:
			managers.ThreadManager.doLater(interval=0.5, func=self.handleMultiDetection)

		self._multiDetectionsHolder.append(payload['siteId'])

		user = 'unknown'
		if payload['modelType'] == 'personal':
			speaker = payload['modelId']
			users = {name.lower(): user for name, user in managers.UserManager.users.items()}
			if speaker in users:
				user = users[speaker].name

		session = managers.DialogSessionManager.preSession(siteId, user)
		managers.broadcast(method='onHotword', exceptions=[self.name], args=[siteId, session])
		managers.ModuleManager.broadcast('onHotword', args=[siteId])


	def handleMultiDetection(self):
		if len(self._multiDetectionsHolder) <= 1:
			self._multiDetectionsHolder = list()
			return

		sessions = managers.DialogSessionManager.sessions
		for sessionId in sessions:
			payload = commons.payload(sessions[sessionId].message)
			if payload['siteId'] != self._multiDetectionsHolder[0]:
				self.endSession(sessionId=sessionId)

		self._multiDetectionsHolder = list()


	# noinspection PyUnusedLocal
	def onSnipsSessionStarted(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = commons.parseSessionId(msg)
		session = managers.DialogSessionManager.addSession(sessionId=sessionId, message=msg)

		if session:
			managers.broadcast(method='onSessionStarted', exceptions=[self.name], args=[session], propagateToModules=True)


	# noinspection PyUnusedLocal
	def onSnipsSessionQueued(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = commons.parseSessionId(msg)
		session = managers.DialogSessionManager.addSession(sessionId=sessionId, message=msg)

		if session:
			managers.broadcast(method='onSessionQueued', exceptions=[self.name], args=[session], propagateToModules=True)


	# noinspection PyUnusedLocal
	def onSnipsStartListening(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = commons.parseSessionId(msg)
		session = managers.DialogSessionManager.getSession(sessionId=sessionId)

		if session:
			managers.broadcast(method='onStartListening', exceptions=[self.name], args=[session], propagateToModules=True)


	# noinspection PyUnusedLocal
	def onSnipsCaptured(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = commons.parseSessionId(msg)
		session = managers.DialogSessionManager.getSession(sessionId=sessionId)

		if session:
			managers.broadcast(method='onCaptured', exceptions=[self.name], args=[session], propagateToModules=True)


	def onSnipsIntentParsed(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = commons.parseSessionId(msg)
		session = managers.DialogSessionManager.getSession(sessionId=sessionId)

		if session:
			session.update(msg)
			managers.broadcast(method='onIntentParsed', exceptions=[self.name], args=[session], propagateToModules=True)

			if managers.ConfigManager.getAliceConfigByName('asr').lower() != 'snips':
				intent = Intent(session.payload['intent']['intentName'].split(':')[1])
				message = mqtt.MQTTMessage(topic=str.encode(str(intent)))
				message.payload = json.dumps(session.payload)
				self.onMessage(client = client, userdata = data, message = message)


	# noinspection PyUnusedLocal
	def onSnipsSessionEnded(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = commons.parseSessionId(msg)
		session = managers.DialogSessionManager.getSession(sessionId)

		if session:
			session.update(msg)
		else:
			managers.ModuleManager.broadcast('onSessionEnded', args=[])
			return

		reason = session.payload['termination']['reason']
		if reason:
			if reason == 'abortedByUser':
				managers.broadcast(method='onUserCancel', exceptions=[self.name], args=[session], propagateToModules=True)
			elif reason == 'timeout':
				managers.broadcast(method='onSessionTimeout', exceptions=[self.name], args=[session], propagateToModules=True)
			elif reason == 'intentNotRecognized':
				# This should never trigger, as "sendIntentNotRecognized" is always set to True, but we never know
				self.onSnipsIntentNotRecognized(None, data, msg)
			elif reason == 'error':
				managers.broadcast(method='onSessionError', exceptions=[self.name], args=[session], propagateToModules=True)
			else:
				managers.broadcast(method='onSessionEnded', exceptions=[self.name], args=[session], propagateToModules=True)

		managers.broadcast(method='onSessionEnded', exceptions=[self.name], args=[session], propagateToModules=True)
		managers.DialogSessionManager.removeSession(sessionId=sessionId)


	# noinspection PyUnusedLocal
	def onSnipsSay(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = commons.parseSessionId(msg)
		payload = commons.payload(msg)

		session = managers.DialogSessionManager.getSession(sessionId)
		if session:
			session.payload = payload
			siteId = session.siteId
		else:
			siteId = commons.parseSiteId(msg)

		if 'text' in payload:
			module = managers.ModuleManager.getModuleInstance('ContextSensitive')
			if module:
				module.addChat(text=payload['text'], siteId=siteId)

		managers.broadcast(method='onSay', exceptions=[self.name], args=[session], propagateToModules=True)


	# noinspection PyUnusedLocal
	def onSnipsSayFinished(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = commons.parseSessionId(msg)
		payload = commons.payload(msg)

		session = managers.DialogSessionManager.getSession(sessionId)
		if session:
			session.payload = payload

		managers.broadcast(method='onSayFinished', exceptions=[self.name], args=[session], propagateToModules=True)


	# noinspection PyUnusedLocal
	def onSnipsIntentNotRecognized(self, client, data, msg: mqtt.MQTTMessage):
		sessionId = commons.parseSessionId(msg)
		session = managers.DialogSessionManager.getSession(sessionId)

		if not session:
			self.ask(text=managers.TalkManager.randomTalk('notUnderstood', module='system'), client=session.siteId)
		else:
			if msg.topic == Intent('UserRandomAnswer'):
				return

			if session.customData and 'module' in session.customData and 'RandomWord' in session.slots:
				module = managers.ModuleManager.getModuleInstance(session.customData['module'])
				if module:
					module.onMessage(Intent('UserRandomAnswer'), session)
					return

			self.reviveSession(session, managers.TalkManager.randomTalk('notUnderstood', module='system'))

		managers.broadcast(method='onIntentNotRecognized', exceptions=[self.name], args=[session], propagateToModules=True)


	def reviveSession(self, session: DialogSession, text: str):
		self.endSession(session.sessionId)
		managers.DialogSessionManager.planSessionRevival(session)
		previousIntent = session.previousIntent[-1] if session.previousIntent else None
		self.ask(text=text, customData=session.customData, previousIntent=previousIntent, intentFilter=session.intentFilter, client=session.siteId)


	def say(self, text, client: str ='default', customData: dict = None, canBeEnqueued: bool = True):
		"""
		Initiate a notification session which is termniated once the text is spoken
		:param canBeEnqueued: bool
		:param text: str Text to say
		:param client: int Where to speak
		:param customData: json object
		"""

		if client == 'all':
			deviceList = managers.DeviceManager.getDevicesByType('AliceSatellite', connectedOnly=True)
			deviceList.append('default')

			for device in deviceList:
				device = device.replace('@mqtt', '')
				self.say(text=text, client=device, customData=customData)
		else:
			if customData is not None:
				if isinstance(customData, dict):
					customData = json.dumps(customData)
				elif isinstance(customData, str):
					pass
				else:
					self._logger.warning('[{}] Ask was provided customdata of unsupported type: {}'.format(self.name, customData))
					customData = ''

			if ' ' in client:
				client = client.replace(' ', '_')

			if managers.ConfigManager.getAliceConfigByName('outputOnSonos') != '1' or (managers.ConfigManager.getAliceConfigByName('outputOnSonos') == '1' and managers.ModuleManager.getModuleInstance('Sonos') is None or not managers.ModuleManager.getModuleInstance('Sonos').anyModuleHere(client)) or not managers.ModuleManager.getModuleInstance('Sonos').active:
				self._mqttClient.publish('hermes/dialogueManager/startSession', json.dumps({
					'siteId'    : client,
					'init'      : {
						'type'                   : 'notification',
						'text'                   : text,
						'sendIntentNotRecognized': True,
						'canBeEnqueued' 		 : canBeEnqueued
					},
					'customData': customData
				}))
			else:
				self._speakOnSonos(text, client)
				self._mqttClient.publish('hermes/dialogueManager/startSession', json.dumps({
					'siteId'    : client,
					'init'      : {
						'type'                   : 'notification',
						'sendIntentNotRecognized': True
					},
					'customData': customData
				}))


	def ask(self, text: str, client: str = 'default', intentFilter: list = None, customData: dict = None, previousIntent: str = '', canBeEnqueued: bool = True):
		"""
		Initiates a new session by asking something and waiting on user answer
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
			self._logger.warning('[{}] Ask was provided customdata of unsupported type: {}'.format(self.name, customData))
			customData = dict()

		user = customData['user'] if customData and 'user' in customData else 'unknown'
		preSession = managers.DialogSessionManager.preSession(client, user)
		if previousIntent:
			preSession.intentHistory.append(previousIntent)

		preSession.intentFilter = intentFilter

		if client == 'all':
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
			'type'                   : 'action',
			'text'                   : text,
			'canBeEnqueued'          : canBeEnqueued,
			'sendIntentNotRecognized': True
		}

		if intentFilter:
			intentList = [str(x).replace('hermes/intent/', '') for x in intentFilter]
			initDict['intentFilter'] = intentList
			initDict['intentFilter'].append(Intent('GlobalStop').justTopic)

		jsonDict['init'] = initDict

		if managers.ConfigManager.getAliceConfigByName('outputOnSonos') != '1' or (managers.ConfigManager.getAliceConfigByName('outputOnSonos') == '1' or managers.ModuleManager.getModuleInstance('Sonos') is None and not managers.ModuleManager.getModuleInstance('Sonos').anyModuleHere(client)) or not managers.ModuleManager.getModuleInstance('Sonos').active:
			if client == 'all':
				deviceList = managers.DeviceManager.getDevicesByType('AliceSatellite', connectedOnly=True)
				deviceList.append('default')

				for device in deviceList:
					device = device.replace('@mqtt', '')
					self.ask(text=text, client=device, intentFilter=intentFilter, customData=customData)
			else:
				self._mqttClient.publish('hermes/dialogueManager/startSession', json.dumps(jsonDict))
		else:
			jsonDict['init']['text'] = ''
			self._mqttClient.publish('hermes/dialogueManager/startSession', json.dumps(jsonDict))

			self._speakOnSonos(text, client)


	def continueDialog(self, sessionId: str, text: str, customData: dict = None, intentFilter: list = None, previousIntent: str = '', slot: str = ''):
		"""
		Continues a dialog
		:param sessionId: int session id to continue
		:param customData: json str
		:param text: str text spoken
		:param intentFilter: array intent filter for user randomTalk
		:param previousIntent: the previous intent that started the dialog continuation
		:param slot: Optional String, requires intentFilter to contain a single value - If set, the dialogue engine will not run the the intent classification on the user response and go straight to slot filling, assuming the intent is the one passed in the intentFilter, and searching the value of the given slot
		"""

		if previousIntent:
			managers.DialogSessionManager.addPreviousIntent(sessionId=sessionId, previousIntent=previousIntent)

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
				self._logger.warning('[{}] ContinueDialog was provided customdata of unsupported type: {}'.format(self.name, customData))

		if intentFilter:
			intentList = [str(x).replace('hermes/intent/', '') for x in intentFilter]
			jsonDict['intentFilter'] = intentList
			jsonDict['intentFilter'].append(Intent('GlobalStop').justTopic)

		if slot:
			jsonDict['slot'] = slot

		session = managers.DialogSessionManager.getSession(sessionId=sessionId)
		session.intentFilter = intentFilter

		if managers.ConfigManager.getAliceConfigByName('outputOnSonos') != '1' or (managers.ConfigManager.getAliceConfigByName('outputOnSonos') == '1' and managers.ModuleManager.getModuleInstance('Sonos') is None or not managers.ModuleManager.getModuleInstance('Sonos').anyModuleHere(session.siteId)) or not managers.ModuleManager.getModuleInstance('Sonos').active:
			self._mqttClient.publish('hermes/dialogueManager/continueSession', json.dumps(jsonDict))
		else:
			jsonDict['text'] = ''
			self._mqttClient.publish('hermes/dialogueManager/continueSession', json.dumps(jsonDict))
			self._speakOnSonos(text, 'default')


	def endTalk(self, sessionId: str = '', text: str = '', client: str = ''):
		"""
		Ends a session by speaking the given text
		:param sessionId: int session id to terminate
		:param text: str Text to speak
		:param client: int Where to speak
		"""
		if not sessionId:
			return

		client = client.replace(' ', '_')

		if managers.ConfigManager.getAliceConfigByName('outputOnSonos') != '1' or (managers.ConfigManager.getAliceConfigByName('outputOnSonos') == '1' and managers.ModuleManager.getModuleInstance('Sonos') is None or not managers.ModuleManager.getModuleInstance('Sonos').anyModuleHere(client)) or not managers.ModuleManager.getModuleInstance('Sonos').active:
			if text:
				self._mqttClient.publish('hermes/dialogueManager/endSession', json.dumps({
					'sessionId': sessionId,
					'text'     : text
				}))
			else:
				self._mqttClient.publish('hermes/dialogueManager/endSession', json.dumps({
					'sessionId': sessionId
				}))
		else:
			self._mqttClient.publish('hermes/dialogueManager/endSession', json.dumps({
				'sessionId': sessionId
			}))
			if text:
				self._speakOnSonos(text, client)


	def endSession(self, sessionId):
		self._mqttClient.publish('hermes/dialogueManager/endSession', json.dumps({
			'sessionId': sessionId
		}))


	def playSound(self, soundFile: str, sessionId: str = '', absolutePath: bool = False, siteId: str = 'default', root: str = '', uid: str = ''):
		"""
		Plays a sound
		:param uid: a unique id for that sound
		:param absolutePath: bool
		:param sessionId: int a session id
		:param soundFile: str The sound file name
		:param siteId: int Where to play the sound
		:param root: If different from default
		"""

		if not root:
			root = os.path.join(commons.rootDir(), 'system', 'sounds')

		if not uid:
			uid = str(uuid.uuid4())

		if not sessionId:
			sessionId = str(uuid.uuid4())

		if siteId == 'all':
			deviceList = managers.DeviceManager.getDevicesByType('AliceSatellite', connectedOnly=True)
			deviceList.append('default')

			for device in deviceList:
				device = device.replace('@mqtt', '')
				self.playSound(sessionId=sessionId, soundFile=soundFile, absolutePath=absolutePath, siteId=device, root=root)
		else:
			if ' ' in siteId:
				siteId = siteId.replace(' ', '_')

			soundFile = soundFile if absolutePath else os.path.join(root, soundFile)

			if not soundFile.endswith('.wav'):
				soundFile += '.wav'

			if not os.path.isfile(soundFile):
				self._logger.error("Sound file {} doesn't exist".format(soundFile))
				return

			with open(soundFile, 'rb') as fp:
				f = fp.read()
				self._mqttClient.publish('hermes/audioServer/{}/playBytes/{}'.format(siteId, uid), payload=bytearray(f))


	def publish(self, topic: str, payload: dict = None, qos: int = 0, retain: bool = False):
		if payload:
			payload = json.dumps(payload)

		self._mqttClient.publish(topic, payload, qos, retain)


	def broadcast(self, topic: str, payload: dict = None, qos: int = 0, retain: bool = False, deviceType: str = 'AliceSatellite'):
		if not payload:
			payload = dict()

		for device in managers.DeviceManager.getDevicesByType(deviceType):
			payload['siteId'] = device.room
			self.publish(topic = topic, payload = payload, qos = qos, retain = retain)

		payload['siteId'] = 'default'
		self.publish(topic=topic, payload=json.dumps(payload), qos=qos, retain=retain)


	@property
	def mqttClient(self):
		return self._mqttClient


	@deprecated
	def _speakOnSonos(self, text, client):
		if text == '':
			return

		subprocess.call(['sudo', commons.rootDir() + '/system/scripts/snipsSuperTTS.sh', '/share/tmp.wav', 'amazon', managers.LanguageManager.activeLanguage, 'US', 'Joanna', 'FEMALE', text, '22050'])

		sonosModule = managers.ModuleManager.getModuleInstance('Sonos')
		if sonosModule:
			sonosModule.aliceSpeak(client)
		else:
			self._logger.error('Tried to speak on Sonos but Sonos module is disabled or missing')


	@staticmethod
	def toggleFeedbackSounds(state='On'):
		"""
		Activates or disables the feedback sounds, on all devices
		:param state: str On or off
		"""

		deviceList = managers.DeviceManager.getDevicesByType('AliceSatellite', connectedOnly=True)
		deviceList.append('default')

		for device in deviceList:
			device = device.replace('@mqtt', '')
			publish.single('hermes/feedback/sound/toggle{}'.format(state.title()), payload=json.dumps({'siteId': device}))
