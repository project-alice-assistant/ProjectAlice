import json
import uuid
from pathlib import Path
from threading import Timer
from typing import Dict, Optional

from paho.mqtt.client import MQTTMessage

from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class DialogManager(Manager):

	DATABASE = {
		'notRecognizedIntents' : [
			'text TEXT NOT NULL'
		]
	}

	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)
		self._sessionsById: Dict[str: DialogSession] = dict()
		self._sessionsBySites: Dict[str: DialogSession] = dict()
		self._endedSessions: Dict[str: DialogSession] = dict()
		self._feedbackSounds: Dict[str: bool] = dict()
		self._sessionTimeouts: Dict[str, Timer] = dict()
		self._revivePendingSessions: Dict[str, DialogSession] = dict()

		self._disabledByDefaultIntents = set()
		self._enabledByDefaultIntents = set()


	def newSession(self, siteId: str, user: str = constants.UNKNOWN_USER, message: MQTTMessage = None) -> DialogSession:
		session = DialogSession(siteId=siteId, user=user, sessionId=str(uuid.uuid4()))

		if message:
			session.update(message)

		self._sessionsById[session.sessionId] = session
		self._sessionsBySites[siteId] = session
		return session


	def newTempSession(self, message: MQTTMessage = None) -> DialogSession:
		siteId = self.Commons.parseSiteId(message)
		session = self.newSession(siteId=siteId, message=message)
		self.startSessionTimeout(sessionId=session.sessionId, tempSession=True)
		return session


	def onWakeword(self, siteId: str, user: str = constants.UNKNOWN_USER):
		self.onHotword(siteId=siteId, user=user)


	def onHotword(self, siteId: str, user: str = constants.UNKNOWN_USER):
		self.logDebug(f'Wakeword detected on site **{siteId}**')

		self._endedSessions[siteId] = self._sessionsById.pop(siteId, None)

		session = self.newSession(siteId=siteId, user=user)
		redQueen = self.SkillManager.getSkillInstance('RedQueen')
		if redQueen and not redQueen.inTheMood(session):
			return

		# Turn off the wakeword component
		self.MqttManager.publish(
			topic=constants.TOPIC_HOTWORD_TOGGLE_OFF,
			payload={
				'siteId'   : siteId,
				'sessionId': session.sessionId
			}
		)

		# Play notification if needed
		if self._feedbackSounds.get('siteId', True):
			self.MqttManager.publish(
				topic=constants.TOPIC_START_SESSION,
				payload={
					'siteId'    : siteId,
					'init'      : {
						'type'                   : 'action',
						'text'                   : self.TalkManager.randomTalk(
							talk='notification',
							skill='system'
						),
						'sendIntentNotRecognized': True,
						'canBeEnqueued'          : False,
						'isHotwordNotification'  : True
					},
					'customData': json.dumps(dict())
				})
		else:
			self.onSayFinished(session=session, uid=str(uuid.uuid4()))


	def onSayFinished(self, session: DialogSession, uid: str = None):
		"""
		Triggers when a Tts say has finished playing.
		If the session has not yet ended and is currently in dialog, we start listening again
		:param uid:
		:param session:
		:return:
		"""

		if not session or session.hasEnded:
			return

		if session.isEnding or session.isNotification:
			if session.isEnding and 0 < session.notUnderstood < int(self.ConfigManager.getAliceConfigByName('notUnderstoodRetries')):
				session.isEnding = False
				self.SkillManager.getSkillInstance('AliceCore').askUpdateUtterance(session=session)
				return

			session.payload['text'] = ''
			self.onEndSession(session=session, reason='nominal')
		else:
			if not session.hasStarted:
				self.onStartSession(
					siteId=session.siteId,
					payload=dict()
				)
			else:
				self.startSessionTimeout(sessionId=session.sessionId)

				self.MqttManager.publish(
					topic=constants.TOPIC_ASR_TOGGLE_ON
				)

				self.MqttManager.publish(
					topic=constants.TOPIC_ASR_START_LISTENING,
					payload={
						'siteId'   : session.siteId,
						'sessionId': session.sessionId
					}
				)


	def startSessionTimeout(self, sessionId: str, tempSession: bool = False, delay: float = 0.0):
		self.cancelSessionTimeout(sessionId=sessionId)

		self._sessionTimeouts[sessionId] = self.ThreadManager.newTimer(
			interval=self.ConfigManager.getAliceConfigByName('sessionTimeout') + delay,
			func=self.sessionTimeout,
			kwargs={
				'sessionId'  : sessionId,
				'tempSession': tempSession
			}
		)


	def cancelSessionTimeout(self, sessionId: str):
		timer = self._sessionTimeouts.pop(sessionId, None)
		if timer:
			timer.cancel()


	def sessionTimeout(self, sessionId: str, tempSession: bool = False):
		"""
		Session has timed out
		:param tempSession:
		:param sessionId:
		:return:
		"""
		session = self.getSession(sessionId)
		if not session:
			return

		if tempSession:
			self.removeSession(sessionId=sessionId)
			return

		session.payload['text'] = ''
		self.onEndSession(session=session, reason='timeout')


	def onSessionStarted(self, session: DialogSession):
		"""
		Session has started, enable Asr and tell it to listen
		:param session:
		:return:
		"""
		self.startSessionTimeout(sessionId=session.sessionId)
		session.hasStarted = True


	def onCaptured(self, session: DialogSession):
		"""
		Asr has captured text, tell it to stop listening
		:param session:
		:return:
		"""
		self.startSessionTimeout(sessionId=session.sessionId)

		self.MqttManager.publish(
			topic=constants.TOPIC_ASR_STOP_LISTENING,
			payload={
				'siteId'   : session.siteId,
				'sessionId': session.sessionId
			}
		)

		cancel = self.LanguageManager.getStrings(
			skill='system',
			key='cancelIntent'
		)

		if session.payload['text'].lower() in cancel:
			session.payload['text'] = ''
			self.onEndSession(session=session, reason='abortedByUser')
			return

		self.MqttManager.publish(
			topic=constants.TOPIC_PLAY_BYTES.format(session.siteId).replace('#', f'{uuid.uuid4()}'),
			payload=bytearray(Path(f'system/sounds/{self.LanguageManager.activeLanguage}/end_of_input.wav').read_bytes())
		)

		# If we've set the filter to a random answer, forge the session and publish an intent captured as UserRandomAnswer
		if session.intentFilter and session.intentFilter[-1] == 'UserRandomAnswer':
			self.forgeUserRandomAnswer(session=session)
			return

		self.MqttManager.publish(
			topic=constants.TOPIC_NLU_QUERY,
			payload={
				'input'       : session.payload['text'],
				'intentFilter': session.intentFilter if session.intentFilter else list(self._enabledByDefaultIntents),
				'sessionId'   : session.sessionId
			}
		)

		skill = self.SkillManager.getSkillInstance('ContextSensitive')
		if skill:
			skill.addUserChat(text=session.payload['text'], siteId=session.siteId)


	def forgeUserRandomAnswer(self, session: DialogSession):
		"""
		Forges a session and sends an onIntentParsed as if an intent was captured
		:param session:
		:return:
		"""
		session.payload['input'] = session.payload['text']
		session.payload.setdefault('intent', dict())
		session.payload['intent']['intentName'] = 'UserRandomAnswer'
		session.payload['intent']['confidenceScore'] = 1.0
		session.payload['alternatives'] = list()
		session.payload['slots'] = list()
		self.onIntentParsed(session)


	def onIntentParsed(self, session: DialogSession):
		"""
		The NLU has parsed an intent, send that intent
		:param session:
		:return:
		"""

		self.MqttManager.publish(
			topic=f'hermes/intent/{session.payload["intent"]["intentName"]}',
			payload={
				'sessionId'    : session.sessionId,
				'customData'   : json.dumps(session.customData),
				'siteId'       : session.siteId,
				'input'        : session.payload['input'],
				'intent'       : session.payload['intent'],
				'slots'        : session.payload['slots'],
				'asrTokens'    : json.dumps(list()),
				'asrConfidence': session.payload['intent']['confidenceScore'],
				'alternatives' : session.payload['alternatives']
			}
		)


	def onNluIntentNotRecognized(self, session: DialogSession):
		"""
		NLU did not recognize any intent
		:param session:
		:return:
		"""
		# If we've set the filter to a random answer, forge the session and publish an intent captured as UserRandomAnswer
		if session.intentFilter and session.intentFilter[-1] == 'UserRandomAnswer':
			self.forgeUserRandomAnswer(session=session)
			return

		self.MqttManager.publish(
			topic=constants.TOPIC_INTENT_NOT_RECOGNIZED,
			payload={
				'siteId'    : session.siteId,
				'customData': json.dumps(session.customData),
				'sessionId' : session.sessionId,
				'input'     : session.payload['input']
			}
		)


	def onNluError(self, session: DialogSession):
		"""
		NLU reported an error
		:param session:
		:return:
		"""
		if not 'error' in session.payload:
			return

		self.logWarning(f'NLU query failed with: {session.payload["error"]}')
		session.payload['text'] = ''
		self.onEndSession(session=session, reason='error')


	def onStartSession(self, siteId: str, payload: dict):
		"""
		Starts a new session
		:param siteId:
		:param payload:
		:return:
		"""

		session = self._sessionsBySites.get(siteId, None)
		if not session:
			# The session was started programmatically, we need to create one
			session = self.newSession(siteId=siteId)
		else:
			if session.hasStarted and not session.hasEnded and 'init' in payload and payload['init'].get('canBeEnqueued', True):
				self.ThreadManager.doLater(interval=1, func=self.onStartSession, kwargs={'siteId': siteId, 'payload': payload})
				return

		hotwordNotification = False

		if 'init' in payload:
			if payload['init']['type'] == 'notification':
				session.isNotification = True
				session.inDialog = False
			else:
				session.isNotification = False
				session.inDialog = True

			if 'isHotwordNotification' in payload['init'] and payload['init']['isHotwordNotification']:
				hotwordNotification = True

		self.MqttManager.publish(
			topic=constants.TOPIC_SESSION_STARTED,
			payload={
				'siteId'    : siteId,
				'sessionId' : session.sessionId,
				'customData': json.dumps(dict())
			}
		)

		text = payload.get('init', dict()).get('text', '')
		if text:
			uid = str(uuid.uuid4())
			self.MqttManager.publish(
				topic=constants.TOPIC_TTS_SAY,
				payload={
					'text'                 : payload['init']['text'],
					'lang'                 : self.LanguageManager.activeLanguageAndCountryCode,
					'siteId'               : siteId,
					'sessionId'            : session.sessionId,
					'uid'                  : uid,
					'isHotwordNotification': hotwordNotification
				}
			)


	def onContinueSession(self, session: DialogSession):
		self.startSessionTimeout(sessionId=session.sessionId)
		session.inDialog = True

		if 'text' in session.payload and session.payload['text']:
			self.MqttManager.publish(
				topic=constants.TOPIC_TTS_SAY,
				payload={
					'text'     : session.payload['text'],
					'lang'     : self.LanguageManager.activeLanguageAndCountryCode,
					'siteId'   : session.siteId,
					'sessionId': session.sessionId
				}
			)


	def onEndSession(self, session: DialogSession, reason: str = 'nominal'):
		text = session.payload.get('text', '')

		if text:
			session.isEnding = True
			self.cancelSessionTimeout(sessionId=session.sessionId)

			self.MqttManager.publish(
				topic=constants.TOPIC_TTS_SAY,
				payload={
					'text'     : session.payload['text'],
					'lang'     : self.LanguageManager.activeLanguageAndCountryCode,
					'siteId'   : session.siteId,
					'sessionId': session.sessionId
				}
			)
		else:
			self.MqttManager.publish(
				topic=constants.TOPIC_SESSION_ENDED,
				payload={
					'siteId'     : session.siteId,
					'sessionId'  : session.sessionId,
					'customData' : json.dumps(session.customData),
					'termination': {
						'reason': reason
					}
				}
			)


	def onSessionEnded(self, session: DialogSession):
		"""
		Session has ended, enable hotword capture and disable Asr
		:param session:
		:return:
		"""
		session.hasEnded = True

		self.MqttManager.publish(
			topic=constants.TOPIC_ASR_TOGGLE_OFF
		)

		self.MqttManager.publish(
			topic=constants.TOPIC_HOTWORD_TOGGLE_ON,
			payload={
				'siteId'   : session.siteId,
				'sessionId': session.sessionId
			}
		)

		self.removeSession(sessionId=session.sessionId)


	def onSessionError(self, session: DialogSession):
		self.MqttManager.publish(
			topic=constants.TOPIC_PLAY_BYTES.format(session.siteId).replace('#', f'{uuid.uuid4()}'),
			payload=bytearray(Path(f'system/sounds/{self.LanguageManager.activeLanguage}/error.wav').read_bytes())
		)


	def toggleFeedbackSound(self, state: str, siteId: str = constants.ALL):
		topic = constants.TOPIC_TOGGLE_FEEDBACK_ON if state == 'on' else constants.TOPIC_TOGGLE_FEEDBACK_OFF

		if siteId == 'all':
			# todo abstract: no hard coded device types!
			devices = self.DeviceManager.getDevicesByType(deviceType=self.DeviceManager.SAT_TYPE, connectedOnly=True)
			for device in devices:
				self.MqttManager.publish(topic=topic, payload={'siteId': device.siteId})

			self.MqttManager.publish(topic=topic, payload={'siteId': self.ConfigManager.getAliceConfigByName('deviceName')})
		else:
			self.MqttManager.publish(topic=topic, payload={'siteId': siteId})


	def onToggleFeedbackOn(self, siteId: str):
		self._feedbackSounds[siteId] = True


	def onToggleFeedbackOff(self, siteId: str):
		self._feedbackSounds[siteId] = False


	def onIntentNotRecognized(self, session: DialogSession):
		if not session.input:
			return

		session.previousInput = session.input
		self.databaseInsert(
			tableName='notRecognizedIntents',
			values={
				'text': session.input
			}
		)


	def getSession(self, sessionId: str) -> Optional[DialogSession]:
		return self._sessionsById.get(sessionId, None)


	def removeSession(self, sessionId: str):
		self.cancelSessionTimeout(sessionId=sessionId)

		session = self._sessionsById.pop(sessionId, None)
		if not session:
			return

		self._endedSessions[sessionId] = session
		self._sessionsBySites.pop(session.siteId, None)


	def increaseSessionTimeout(self, session: DialogSession, interval: float):
		"""
		This is used by the Tts, so that the timeout is set to the duration of the speech at least
		:param session:
		:param interval:
		:return:
		"""
		if session.sessionId not in self._sessionsById:
			return

		self.startSessionTimeout(sessionId=session.sessionId, delay=interval)


	@property
	def sessions(self) -> Dict[str, DialogSession]:
		return self._sessionsById


	@property
	def sessionsBySites(self) -> Dict[str, DialogSession]:
		return self._sessionsBySites


	def addDisabledByDefaultIntent(self, intent: str):
		self._disabledByDefaultIntents.add(intent)
		# Remove it from enabled intents in case it exists
		if intent in self._enabledByDefaultIntents:
			self._enabledByDefaultIntents.remove(intent)


	def addEnabledByDefaultIntent(self, intent: str):
		self._enabledByDefaultIntents.add(intent)


	def cleanNotRecognizedIntent(self, text: str):
		self.DatabaseManager.delete(
			tableName='notRecognizedIntents',
			callerName=self.name,
			values={
				'text': text
			}
		)
