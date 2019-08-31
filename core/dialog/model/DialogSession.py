# -*- coding: utf-8 -*-

from paho.mqtt.client import MQTTMessage

from core.commons import commons

class DialogSession:
	def __init__(self, siteId):
		self._siteId = siteId
		self._sessionId = ''
		self._user = 'unknown'
		self._message = None
		self._slots = dict()
		self._slotsAsObjects = dict()
		self._customData = dict()
		self._payload = dict()
		self._intentHistory = list()
		self._intentFilter = list()


	def extend(self, message: MQTTMessage, sessionId: str = None):
		if sessionId:
			self._sessionId = sessionId

		self._message = message
		self._parseMessage()


	def update(self, message: MQTTMessage):
		self._message = message
		self._updateSessionData()


	def reviveOldSession(self, session):
		self._payload = session.payload
		self._slots = session.slots
		self._slotsAsObjects = session.slotsAsObjects
		self._customData = session.customData
		self._user = session.user
		self._message = session.message
		self._intentHistory = session.intentHistory
		self._intentFilter = session.intentFilter


	def _parseMessage(self):
		self._payload = commons.payload(self._message)
		self._slots = commons.parseSlots(self._message)
		self._slotsAsObjects = commons.parseSlotsToObjects(self._message)
		self._customData = commons.parseCustomData(self._message)


	def _updateSessionData(self):
		self._payload = commons.payload(self._message)
		self._slots = {**self._slots, **commons.parseSlots(self._message)}
		self._slotsAsObjects = {**self._slotsAsObjects, **commons.parseSlotsToObjects(self._message)}
		self._customData = {**self._customData, **commons.parseCustomData(self._message)}


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
		This returns the slot raw value, what what really heard / captured, so it can be a synonym per exemple
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
	def previousIntent(self) -> list:
		return self._intentHistory[-1] if self._intentHistory else ''


	@property
	def intentFilter(self) -> list:
		return self._intentFilter


	@intentFilter.setter
	def intentFilter(self, value: list):
		self._intentFilter = value


	def __repr__(self):
		output = "[{}] -> ".format(self.__class__.__name__) + "{"
		output += "_siteId='" + str(self._siteId)+"', "
		output += "_sessionId='" + str(self._sessionId)+"', "
		output += "_user='" + str(self._user)+"', "
		output += "_message='" + str(self._message)+"', "
		output += "_slots='" + str(self._slots)+"', "
		output += "_slotsAsObjects='" + str(self._slotsAsObjects)+"', "
		output += "_customData='" + str(self._customData)+"', "
		output += "_payload='" + str(self._payload)+"', "
		output += "_intentHistory='" + str(self._intentHistory)+"', "
		output += "EndOfObject}"
		return output
