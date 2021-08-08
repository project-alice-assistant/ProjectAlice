#  Copyright (c) 2021
#
#  This file, MultiIntentManager.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:47 CEST

from collections import deque

from paho.mqtt.client import MQTTMessage

from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model import DialogSession
from core.dialog.model.MultiIntent import MultiIntent
from core.util.Decorators import deprecated


class MultiIntentManager(Manager):

	def __init__(self):
		super().__init__()
		self._multiIntents = dict()


	@property
	def multiIntents(self) -> dict:
		return self._multiIntents


	def processMessage(self, message: MQTTMessage) -> bool:
		sessionId = self.Commons.parseSessionId(message)
		session = self.DialogManager.getSession(sessionId)
		if not session or self.isProcessing(sessionId):
			return False

		payload = session.payload
		if 'input' in payload:
			separators = self.LanguageManager.getStrings('intentSeparator')
			GLUE_SPLITTER = '__multi_intent__'
			userInput = payload['input'].lower()

			for separator in separators:
				userInput = userInput.replace(separator, GLUE_SPLITTER)

			if GLUE_SPLITTER in userInput:
				self._multiIntents[session.sessionId] = MultiIntent(
					session=session,
					processedString=userInput,
					intents=deque(userInput.split(GLUE_SPLITTER)))

				return self.processNextIntent(session)

		return False


	def processNextIntent(self, session: DialogSession) -> bool:
		multiIntent = self._multiIntents[session.sessionId]
		intent = multiIntent.getNextIntent()
		if not intent:
			return False

		session.input = intent
		self.MqttManager.publish(
			topic=constants.TOPIC_TEXT_CAPTURED,
			payload={
				'sessionId': session.sessionId,
				'text': intent,
				'device': session.deviceUid,
				'likelihood': 1,
				'seconds': 1
			})
		return True


	@deprecated
	def queryNLU(self, session: DialogSession, string: str):
		self.MqttManager.publish(topic=constants.TOPIC_NLU_QUERY, payload={
			'input'       : string,
			'sessionId'   : session.sessionId,
			'intentFilter': session.intentFilter
		})


	def removeSession(self, sessionId: str):
		del self._multiIntents[sessionId]


	def isProcessing(self, sessionId: str):
		return sessionId in self._multiIntents
