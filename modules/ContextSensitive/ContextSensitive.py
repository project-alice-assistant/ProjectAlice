# -*- coding: utf-8 -*-

import json

import core.base.Managers    as managers
from core.base.model.Intent import Intent
from core.base.model.Module import Module
from core.dialog.model.DialogSession import DialogSession


class ContextSensitive(Module):
	_INTENT_DELETE_THIS = Intent('DeleteThis', isProtected=True)
	_INTENT_REPEAT_THIS = Intent('RepeatThis', isProtected=True)
	_INTENT_EDIT_THIS = Intent('EditThis', isProtected=True)
	_INTENT_ANSWER_YES_OR_NO = Intent('AnswerYesOrNo', isProtected=True)


	def __init__(self):
		self._SUPPORTED_INTENTS = [
			self._INTENT_DELETE_THIS,
			self._INTENT_REPEAT_THIS,
			self._INTENT_EDIT_THIS
		]

		self._history = list()
		self._sayHistory = dict()

		super().__init__(self._SUPPORTED_INTENTS)


	def onMessage(self, intent: str, session: DialogSession) -> bool:
		if not self.filterIntent(intent, session):
			return False

		sessionId = session.sessionId
		siteId = session.siteId

		if intent == self._INTENT_DELETE_THIS:
			modules = managers.ModuleManager.getModules()
			for module in modules.values():
				try:
					if module['instance'].onContextSensitiveDelete(sessionId):
						managers.MqttServer.endTalk(sessionId=sessionId)
						return True
				except Exception:
					continue

		elif intent == self._INTENT_EDIT_THIS:
			modules = managers.ModuleManager.getModules()
			for module in modules.values():
				try:
					if module['instance'].onContextSensitiveEdit(sessionId):
						managers.MqttServer.endTalk(sessionId=sessionId)
						return True
				except:
					continue

		elif intent == self._INTENT_REPEAT_THIS:
			managers.MqttServer.endTalk(sessionId, text=self.getLastChat(siteId=siteId))
			return True

		managers.MqttServer.endTalk(sessionId, text=self.randomTalk('didntUnderstand'))
		return True


	def addToMessageHistory(self, session: DialogSession):
		if session.message.topic in self._SUPPORTED_INTENTS or session.message.topic == self._INTENT_ANSWER_YES_OR_NO or 'intent' not in session.message.topic:
			return

		try:
			customData = session.customData

			if 'speaker' not in customData:
				customData['speaker'] = session.user
				data = session.payload
				data['customData'] = customData
				session.payload = json.dumps(data)

			self._history.append(session)

			if len(self._history) > 10:
				self._history.pop(0)
		except Exception as e:
			self._logger.error('Error in {} module: {}'.format(self.name, e))


	def lastMessage(self):
		return self._history[len(self._history) - 1]


	def addChat(self, text, siteId):
		if siteId not in self._sayHistory.keys():
			self._sayHistory[siteId] = list()

		self._sayHistory[siteId].append(text)

		if len(self._sayHistory[siteId]) > 10:
			self._sayHistory[siteId].pop(0)


	def getLastChat(self, siteId):
		if siteId not in self._sayHistory or len(self._sayHistory[siteId]) <= 0:
			return self.randomTalk('nothing')

		return self._sayHistory[siteId][len(self._sayHistory[siteId]) - 1]
