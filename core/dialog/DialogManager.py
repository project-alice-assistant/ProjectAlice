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
		self._sessions: Dict[str: DialogSession] = dict()
		self._terminatedSessions: Dict[str: DialogSession] = dict()
		self._endedSessions: Dict[str: DialogSession] = dict()
		self._feedbackSounds: Dict[str: bool] = dict()
		self._sessionTimeouts: Dict[str, Timer] = dict()


	def onHotword(self, siteId: str, user: str = constants.UNKNOWN_USER):
		self._endedSessions[siteId] = self._sessions.pop(siteId, None)

		session = DialogSession(siteId=siteId, user=user, sessionId=str(uuid.uuid4()))
		self._sessions[session.sessionId] = session

		# Turn off the wakeword component
		self.MqttManager.publish(
			topic=constants.TOPIC_HOTWORD_TOGGLE_OFF,
			payload={
				'siteId': siteId,
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

		self.MqttManager.publish(
			topic=constants.TOPIC_SESSION_STARTED,
			payload={
				'siteId': siteId,
				'sessionId': sessionId,
				'customData': dict()
			}
		)

		# Schedule timeout for this session
		self._sessionTimeouts[sessionId] = self.ThreadManager.newTimer(
			interval=self.ConfigManager.getAliceConfigByName('sessionTimeout'),
			func=self.sessionTimeout,
			kwargs={
				'sessionId': sessionId
			}
		)


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
				'siteId'    : session.siteId,
				'sessionId' : sessionId,
				'customData': session.customData,
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
		self.MqttManager.publish(
			topic=constants.TOPIC_ASR_TOGGLE_ON
		)

		self.MqttManager.publish(
			topic=constants.TOPIC_ASR_START_LISTENING,
			payload={
				'siteId': session.siteId,
				'sessionId': session.sessionId
			}
		)


	def onCaptured(self, session: DialogSession):
		"""
		ASR has captured text, tell it to stop listening
		:param session:
		:return:
		"""
		self.MqttManager.publish(
			topic=constants.TOPIC_ASR_STOP_LISTENING,
			payload={
				'siteId': session.siteId,
				'sessionId': session.sessionId
			}
		)

		self.MqttManager.publish(
			topic=constants.TOPIC_NLU_QUERY,
			payload={
				'input': session.payload['text'],
				'intentFilter': session.intentFilter,
				'sessionId': session.sessionId
			}
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
				'input': session.payload['text'],
				'intentFilter': session.intentFilter,
				'sessionId': session.sessionId
			}
		)


	def onIntentNotRecognized(self, session):
		"""
		NLU did not recognize any intent
		:param session:
		:return:
		"""
		self.MqttManager.publish(
			topic=f'hermes/intent/',
			payload={
				'input': session.payload['text'],
				'intentFilter': session.intentFilter,
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
			topic=constants.TOPIC_HOTWORD_TOGGLE_ON,
			payload={
				'siteId': session.siteId,
				'sessionId': session.sessionId
			}
		)

		self.MqttManager.publish(
			topic=constants.TOPIC_ASR_TOGGLE_OFF
		)

		self.onContinueSession(session=session)


	def onContinueSession(self, session: DialogSession):
		if session.sessionId not in self._sessionTimeouts:
			return

		timer = self._sessionTimeouts[session.sessionId]
		timer.cancel()


	def onToggleFeedbackOn(self, siteId: str):
		self._feedbackSounds[siteId] = True


	def onToggleFeedbackOff(self, siteId: str):
		self._feedbackSounds[siteId] = False


	def getSession(self, sessionId: str) -> Optional[DialogSession]:
		return self._sessions.get(sessionId, None)


	def removeSession(self, sessionId: str):
		if sessionId in self._sessions:
			self._terminatedSessions[sessionId] = self._sessions.pop(sessionId)
