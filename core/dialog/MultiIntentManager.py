from paho.mqtt.client import MQTTMessage

from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model import DialogSession
from core.dialog.model.MultiIntent import MultiIntent


class MultiIntentManager(Manager):

	def __init__(self):
		super().__init__()
		self._multiIntents = dict()


	@property
	def multiIntents(self) -> dict:
		return self._multiIntents


	def processMessage(self, message: MQTTMessage) -> bool:
		sessionId = self.Commons.parseSessionId(message)
		session = self.DialogSessionManager.getSession(sessionId)
		if not session or self.isProcessing(sessionId):
			return False

		payload = session.payload
		if 'input' in payload:
			separators = self.LanguageManager.getStrings('intentSeparator')
			GLUE_SPLITTER = '__multi_intent__'
			userInput = payload['input']

			for separator in separators:
				userInput.replace(separator, GLUE_SPLITTER)

			if GLUE_SPLITTER in userInput:
				multiIntent = MultiIntent(session, userInput)

				for string in userInput.split(GLUE_SPLITTER):
					multiIntent.addIntent(string)

				self._multiIntents[session.sessionId] = multiIntent
				return self.processNextIntent(session.sessionId)
			else:
				return False
		else:
			return False


	def processNextIntent(self, sessionId: str) -> bool:
		multiIntent = self._multiIntents[sessionId]
		intent = multiIntent.getNextIntent()
		if not intent:
			return False

		self._queryNLU(multiIntent.session, string=intent)
		return True


	def _queryNLU(self, session: DialogSession, string: str):
		self.MqttManager.publish(topic=constants.TOPIC_NLU_QUERY, payload={
			'input': string,
			'sessionId': session.sessionId,
			'intentFilter': session.intentFilter
		})


	def removeSession(self, sessionId: str):
		del self._multiIntents[sessionId]


	def isProcessing(self, sessionId: str):
		return sessionId in self._multiIntents
