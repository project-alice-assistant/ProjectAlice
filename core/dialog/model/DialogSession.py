from __future__ import annotations
from textwrap import dedent
from paho.mqtt.client import MQTTMessage

from core.base.SuperManager import SuperManager
from core.base.model import Intent
from core.commons import constants


class DialogSession:
	def __init__(self, siteId):
		self._siteId = siteId
		self._sessionId = ''
		self._user = constants.UNKNOWN_USER
		self._message = None
		self._slots = dict()
		self._slotsAsObjects = dict()
		self._customData = dict()
		self._payload = dict()
		self._intentHistory = list()
		self._intentFilter = list()
		self._notUnderstood = 0
		self._currentState = constants.DEFAULT


	def extend(self, message: MQTTMessage, sessionId: str = None):
		if sessionId:
			self._sessionId = sessionId

		self._message = message
		self._parseMessage()


	def update(self, message: MQTTMessage):
		self._message = message
		self._updateSessionData()


	def reviveOldSession(self, session: DialogSession):
		self._payload = session.payload
		self._slots = session.slots
		self._slotsAsObjects = session.slotsAsObjects
		self._customData = session.customData
		self._user = session.user
		self._message = session.message
		self._intentHistory = session.intentHistory
		self._intentFilter = session.intentFilter
		self._notUnderstood = session.notUnderstood
		self._currentState = session.currentState


	def _parseMessage(self):
		self._payload = SuperManager.getInstance().commons.payload(self._message)
		self._slots = SuperManager.getInstance().commons.parseSlots(self._message)
		self._slotsAsObjects = SuperManager.getInstance().commons.parseSlotsToObjects(self._message)
		self._customData = SuperManager.getInstance().commons.parseCustomData(self._message)


	def _updateSessionData(self):
		self._payload = SuperManager.getInstance().commons.payload(self._message)
		self._slots = {**self._slots, **SuperManager.getInstance().commons.parseSlots(self._message)}
		self._slotsAsObjects = {**self._slotsAsObjects, **SuperManager.getInstance().commons.parseSlotsToObjects(self._message)}
		self._customData = {**self._customData, **SuperManager.getInstance().commons.parseCustomData(self._message)}


	def addToHistory(self, intent: Intent):
		self._intentHistory.append(intent)


	@property
	def slots(self) -> dict:
		return self._slots


	@property
	def slotsAsObjects(self) -> dict:
		return self._slotsAsObjects


	def slotValue(self, slotName: str, index: int = 0) -> str:
		"""
		This returns the slot master value, not necesserly what was heard / captured
		"""
		if slotName in self._slotsAsObjects:
			return self.slotsAsObjects[slotName][index].value['value']
		else:
			return ''


	def slotRawValue(self, slotName: str) -> str:
		"""
		This returns the slot raw value, what whas really heard / captured, so it can be a synonym per exemple
		"""
		return self._slots.get(slotName, '')


	@property
	def customData(self) -> dict:
		return self._customData


	@property
	def payload(self) -> dict:
		return self._payload


	@payload.setter
	def payload(self, value: dict):
		self._payload = value


	@property
	def siteId(self) -> str:
		return self._siteId


	@property
	def sessionId(self) -> str:
		return self._sessionId


	@property
	def user(self) -> str:
		return self._user


	@user.setter
	def user(self, user: str):
		self._user = user


	@sessionId.setter
	def sessionId(self, sessionId: str):
		self._sessionId = sessionId


	@property
	def message(self) -> MQTTMessage:
		return self._message


	@message.setter
	def message(self, message: MQTTMessage):
		self._message = message


	@property
	def intentHistory(self) -> list:
		return self._intentHistory


	@intentHistory.setter
	def intentHistory(self, value: list):
		self._intentHistory = value.copy()


	@property
	def previousIntent(self) -> Intent:
		return self._intentHistory[-1] if self._intentHistory else None


	@property
	def intentFilter(self) -> list:
		return self._intentFilter


	@intentFilter.setter
	def intentFilter(self, value: list):
		self._intentFilter = value


	@property
	def notUnderstood(self) -> int:
		return self._notUnderstood


	@notUnderstood.setter
	def notUnderstood(self, value: int):
		self._notUnderstood = value


	@notUnderstood.deleter
	def notUnderstood(self):
		self._notUnderstood = 0


	@property
	def currentState(self) -> str:
		return self._currentState


	@currentState.setter
	def currentState(self, value: str):
		self._currentState = value


	def __repr__(self) -> str:
		return dedent(f'''\
			[{self.__class__.__name__}] -> [
				siteId: "{self.siteId}",
				sessionId: "{self._sessionId}",
				user: "{self._user}",
				message: "{self._message.topic}",
				slots: "{self._slots}",
				slotsAsObject: "{self._slotsAsObjects}",
				customData: "{self._customData}",
				payload: "{self._payload}",
				previousIntent: "{self.previousIntent}",
				intentHistory: "{self._intentHistory}",
				intentFilter: "{self._intentFilter}",
				notUnderstood: "{self._notUnderstood}"
			]
		''')
