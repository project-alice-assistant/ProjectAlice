import uuid
from pathlib import Path
from threading import Timer
from typing import Dict, List, Optional

from paho.mqtt.client import MQTTMessage

from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class DialogManager(Manager):
	"""
	onHotword is the real starting point. It creates a new session that will be held throughout the entire dialogue

	This handles the hermes protocol but adds none standard payload informations that were not originally thought by the Snips team

	This contains a hack to make sure sessions are started only when the notification has finished playing
	"""


	def __init__(self):
		super().__init__()
		self._sessionsById: Dict[str: DialogSession] = dict()
		self._sessionsBySites: Dict[str: DialogSession] = dict()
		self._endedSessions: Dict[str: DialogSession] = dict()
		self._feedbackSounds: Dict[str: bool] = dict()
		self._sessionTimeouts: Dict[str, Timer] = dict()
		self._revivePendingSessions: Dict[str, DialogSession] = dict()
		self._says: List[str] = list()

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


	def onHotword(self, siteId: str, user: str = constants.UNKNOWN_USER):
		self._endedSessions[siteId] = self._sessionsById.pop(siteId, None)

		session = self.newSession(siteId=siteId, user=user)

		# Turn off the wakeword component
		self.MqttManager.publish(
			topic=constants.TOPIC_HOTWORD_TOGGLE_OFF,
			payload={
				'siteId'   : siteId,
				'sessionId': session.sessionId
			}
		)

		requestId = str(uuid.uuid4())

		# Play notification if needed
		if self._feedbackSounds.get('siteId', True):
			# Adding the session id is custom!
			uid = str(uuid.uuid4())
			self.addSayUuid(uid)
			self.MqttManager.publish(
				topic=constants.TOPIC_TTS_SAY,
				payload={
					'text'     : self.TalkManager.randomTalk(
						talk='notification',
						skill='system'
					),
					'lang'     : self.LanguageManager.activeLanguageAndCountryCode,
					'siteId'   : siteId,
					'sessionId': session.sessionId,
					'uid'      : uid
				}
			)
		else:
			self.onSayFinished(session=session, uid=requestId)


	def onSayFinished(self, session: DialogSession, uid: str = None):
		"""
		Triggers when a TTS say has finished playing.
		If the session has not yet ended and is currently in dialog, we start listening again
		:param uid:
		:param session:
		:return:
		"""

		if session.hasEnded or not uid or not uid in self._says:
			return

		self._says.remove(uid)

		if session.isEnding:
			self.MqttManager.publish(
				topic=constants.TOPIC_SESSION_ENDED,
				payload={
					'siteId'     : session.siteId,
					'sessionId'  : session.sessionId,
					'customData' : session.customData,
					'termination': {
						'reason': 'nominal'
					}
				}
			)
		else:
			if not session.inDialog:
				self.onStartSession(
					siteId=session.siteId,
					payload=dict()
				)
			else:
				self.onSessionStarted(session=session)


	def startSessionTimeout(self, sessionId: str, tempSession: bool = False):
		self.cancelSessionTimeout(sessionId=sessionId)

		self._sessionTimeouts[sessionId] = self.ThreadManager.newTimer(
			interval=self.ConfigManager.getAliceConfigByName('sessionTimeout'),
			func=self.sessionTimeout,
			kwargs={
				'sessionId': sessionId,
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


		self.MqttManager.publish(
			topic=constants.TOPIC_SESSION_ENDED,
			payload={
				'siteId'     : session.siteId,
				'sessionId'  : sessionId,
				'customData' : session.customData,
				'termination': {
					'reason': 'timeout'
				}
			}
		)


	def onSessionStarted(self, session: DialogSession):
		"""
		Session has started, enable ASR and tell it to listen
		:param session:
		:return:
		"""
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


	def onCaptured(self, session: DialogSession):
		"""
		ASR has captured text, tell it to stop listening
		:param session:
		:return:
		"""
		self.cancelSessionTimeout(sessionId=session.sessionId)

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
			self.MqttManager.publish(
				topic=constants.TOPIC_SESSION_ENDED,
				payload={
					'siteId'     : session.siteId,
					'sessionId'  : session.sessionId,
					'customData' : session.customData,
					'termination': {
						'reason': 'abortedByUser'
					}
				}
			)
			return

		self.MqttManager.publish(
			topic=constants.TOPIC_PLAY_BYTES.format(session.siteId).replace('#', f'{uuid.uuid4()}'),
			payload=bytearray(Path('assistant/custom_dialogue/sound/end_of_input.wav').read_bytes())
		)

		self.MqttManager.publish(
			topic=constants.TOPIC_NLU_QUERY,
			payload={
				'input'       : session.payload['text'],
				'intentFilter': session.intentFilter if session.intentFilter else list(self._enabledByDefaultIntents),
				'sessionId'   : session.sessionId
			}
		)


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
				'customData'   : session.customData,
				'siteId'       : session.siteId,
				'input'        : session.payload['input'],
				'intent'       : session.payload['intent'],
				'slots'        : session.payload['slots'],
				'asrTokens'    : [],
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
		self.MqttManager.publish(
			topic=constants.TOPIC_INTENT_NOT_RECOGNIZED,
			payload={
				'siteId'    : session.siteId,
				'customData': session.customData,
				'sessionId' : session.sessionId,
				'input'     : session.payload['input']
			}
		)


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

		self.MqttManager.publish(
			topic=constants.TOPIC_SESSION_STARTED,
			payload={
				'siteId'    : siteId,
				'sessionId' : session.sessionId,
				'customData': dict()
			}
		)

		if 'init' in payload:
			if payload['init']['type'] == 'notification':
				session.isEnding = True

			uid = str(uuid.uuid4())
			self.addSayUuid(uid)
			self.MqttManager.publish(
				topic=constants.TOPIC_TTS_SAY,
				payload={
					'text'     : payload['init']['text'],
					'lang'     : self.LanguageManager.activeLanguageAndCountryCode,
					'siteId'   : siteId,
					'sessionId': session.sessionId,
					'uid'      : uid
				}
			)


	def onContinueSession(self, session: DialogSession):
		self.startSessionTimeout(sessionId=session.sessionId)
		self.MqttManager.publish(
			topic=constants.TOPIC_TTS_SAY,
			payload={
				'text'     : session.payload['text'],
				'lang'     : self.LanguageManager.activeLanguageAndCountryCode,
				'siteId'   : session.siteId,
				'sessionId': session.sessionId
			}
		)


	def onEndSession(self, session: DialogSession):
		text = session.payload['text']

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
					'customData' : session.customData,
					'termination': {
						'reason': 'nominal'
					}
				}
			)


	def onSessionEnded(self, session: DialogSession):
		"""
		Session has ended, enable hotword capture and disable ASR
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


	def addSayUuid(self, uid: str):
		self._says.append(uid)


	def onToggleFeedbackOn(self, siteId: str):
		self._feedbackSounds[siteId] = True


	def onToggleFeedbackOff(self, siteId: str):
		self._feedbackSounds[siteId] = False


	def getSession(self, sessionId: str) -> Optional[DialogSession]:
		return self._sessionsById.get(sessionId, None)


	def removeSession(self, sessionId: str):
		self.cancelSessionTimeout(sessionId=sessionId)

		session = self._sessionsById.pop(sessionId, None)
		if not session:
			return

		self._endedSessions[sessionId] = session
		self._sessionsBySites.pop(session.siteId)


	@property
	def sessions(self) -> Dict[str, DialogSession]:
		return self._sessionsById


	def addDisabledByDefaultIntent(self, intent: str):
		self._disabledByDefaultIntents.add(intent)
		# Remove it from enabled intents in case it exists
		if intent in self._enabledByDefaultIntents:
			self._enabledByDefaultIntents.remove(intent)


	def addEnabledByDefaultIntent(self, intent: str):
		self._enabledByDefaultIntents.add(intent)
