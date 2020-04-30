import uuid
from pathlib import Path
from threading import Timer
from typing import Dict, Optional

from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class DialogManager(Manager):
	"""
	onHotword is the real starting point. It creates a new session that will be held throughout the entire dialogue

	This handles the hermes protocol but adds none standard payload informations that were not originally thought by the Snips team

	This contains a hack to make sure sessions are started only when the chime has finished playing
	"""


	def __init__(self):
		super().__init__()
		self._sessionsById: Dict[str: DialogSession] = dict()
		self._sessionsBySites: Dict[str: DialogSession] = dict()
		self._endedSessions: Dict[str: DialogSession] = dict()
		self._feedbackSounds: Dict[str: bool] = dict()
		self._sessionTimeouts: Dict[str, Timer] = dict()


	def onHotword(self, siteId: str, user: str = constants.UNKNOWN_USER):
		self._endedSessions[siteId] = self._sessionsById.pop(siteId, None)

		session = DialogSession(siteId=siteId, user=user, sessionId=str(uuid.uuid4()))
		self._sessionsById[session.sessionId] = session
		self._sessionsBySites[siteId] = session

		# Turn off the wakeword component
		self.MqttManager.publish(
			topic=constants.TOPIC_HOTWORD_TOGGLE_OFF,
			payload={
				'siteId'   : siteId,
				'sessionId': session.sessionId
			}
		)

		requestId = str(uuid.uuid4())

		# Play chime if needed
		if self._feedbackSounds.get('siteId', True):
			# Adding the session id is custom!
			self.MqttManager.publish(
				topic=constants.TOPIC_PLAY_BYTES.format(siteId).replace('#', f'{session.sessionId}/{requestId}'),
				payload=bytearray(Path('assistant/custom_dialogue/sound/start_of_input.wav').read_bytes())
			)
		else:
			self.onPlayBytesFinished(requestId=requestId, siteId=siteId, sessionId=session.sessionId)


	def onPlayBytesFinished(self, requestId: str, siteId: str, sessionId: str = None):
		"""
		This is totally a hack, we report the session has started only when the sound has finished playing
		:param sessionId: str
		:param requestId: str
		:param siteId: str
		:return: none
		"""

		if not sessionId:
			return

		session = self._sessionsById.get(sessionId, None)

		if not session:
			return

		if not session.inDialog:
			self.onStartSession(
				siteId=siteId,
				init=dict(),
				customData=dict()
			)
		else:
			self.onSessionStarted(session=session)


	def onSayFinished(self, session: DialogSession):
		"""
		Triggers when a TTS say has finished playing.
		If the session is currently in dialog, we start listening again
		:param session:
		:return:
		"""
		if session.inDialog:
			self.onSessionStarted(session=session)


	def startSessionTimeout(self, sessionId: str):
		self.cancelSessionTimeout(sessionId=sessionId)

		self._sessionTimeouts[sessionId] = self.ThreadManager.newTimer(
			interval=self.ConfigManager.getAliceConfigByName('sessionTimeout'),
			func=self.sessionTimeout,
			kwargs={
				'sessionId': sessionId
			}
		)


	def cancelSessionTimeout(self, sessionId: str):
		timer = self._sessionTimeouts.pop(sessionId, None)
		if timer:
			timer.cancel()


	def sessionTimeout(self, sessionId: str):
		"""
		Session has timed out
		:param sessionId:
		:return:
		"""
		session = self.getSession(sessionId)
		if not session:
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

		self.MqttManager.publish(
			topic=constants.TOPIC_NLU_QUERY,
			payload={
				'input'       : session.payload['text'],
				'intentFilter': session.intentFilter,
				'sessionId'   : session.sessionId
			}
		)

		self.MqttManager.publish(
			topic=constants.TOPIC_PLAY_BYTES.format(session.siteId).replace('#', f'{uuid.uuid4()}'),
			payload=bytearray(Path('assistant/custom_dialogue/sound/end_of_input.wav').read_bytes())
		)


	def onIntentParsed(self, session: DialogSession):
		"""
		The NLU has parsed an intent, send that intent
		:param session:
		:return:
		"""
		self.MqttManager.publish(
			topic=f'hermes/intent/',
			payload={
				'input'       : session.payload['text'],
				'intentFilter': session.intentFilter,
				'sessionId'   : session.sessionId
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


	def onStartSession(self, siteId: str, init: dict, customData: dict):
		"""
		Starts a new session
		:param siteId:
		:param init:
		:param customData:
		:return:
		"""
		session = self._sessionsBySites.get(siteId, None)
		if not session:
			return

		self.MqttManager.publish(
			topic=constants.TOPIC_SESSION_STARTED,
			payload={
				'siteId'    : siteId,
				'sessionId' : session.sessionId,
				'customData': dict()
			}
		)

		if init:
			if init['type'] == 'notification':
				self.MqttManager.publish(
					topic=constants.TOPIC_TTS_SAY,
					payload={
						'text'     : init['text'],
						'lang'     : self.LanguageManager.activeLanguageAndCountryCode,
						'siteId'   : siteId,
						'sessionId': session.sessionId
					}
				)


	def onContinueSession(self, session: DialogSession):
		print('im here')
		self.MqttManager.publish(
			topic=constants.TOPIC_TTS_SAY,
			payload={
				'text'     : session.payload['text'],
				'lang'     : self.LanguageManager.activeLanguageAndCountryCode,
				'siteId'   : session.siteId,
				'sessionId': session.sessionId
			}
		)


	def onSessionEnded(self, session: DialogSession):
		"""
		Session has ended, enable hotword capture and disable ASR
		:param session:
		:return:
		"""
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
