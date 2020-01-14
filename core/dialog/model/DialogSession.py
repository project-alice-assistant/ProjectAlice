from __future__ import annotations

from typing import Optional, Any

from paho.mqtt.client import MQTTMessage
import attr

from core.base.model import Intent
from core.commons import constants


#TODO: improve typing information for dicts and lists using typing.List
# and typing.Dict
@attr.s(slots=True, auto_attribs=True)
class DialogSession:
	siteId: str
	sessionId: str = ''
	user: str = constants.UNKNOWN_USER
	message: MQTTMessage = None
	intentName: str = ''
	slots: dict = attr.Factory(dict))
	slotsAsObjects: dict = attr.Factory(dict)
	customData: dict = attr.Factory(dict)
	payload: dict = attr.Factory(dict)
	intentHistory: list = attr.Factory(list)
	intentFilter: list = attr.Factory(list)
	notUnderstood: int = 0
	currentState: str = constants.DEFAULT
	isAPIGenerated: bool = False


	def extend(self, message: MQTTMessage, sessionId: str = None):
		if sessionId:
			self.sessionId = sessionId

		from core.commons.CommonsManager import CommonsManager
		self.message = message
		self.intentName = message.topic
		self.payload = CommonsManager.payload(message)
		self.slots = CommonsManager.parseSlots(message)
		self.slotsAsObjects = CommonsManager.parseSlotsToObjects(message)
		self.customData = CommonsManager.parseCustomData(message)


	def update(self, message: MQTTMessage):
		from core.commons.CommonsManager import CommonsManager
		self.message = message
		self.intentName = message.topic
		self.payload = CommonsManager.payload(message)
		self.slots.update(CommonsManager.parseSlots(message))
		self.slotsAsObjects.update(CommonsManager.parseSlotsToObjects(message))
		self.customData.update(CommonsManager.parseCustomData(message))


	def reviveOldSession(self, session: DialogSession):
		"""
		Revives old session keeping siteId, sessionId and isAPIGenerated from the
		new session
		"""
		self.payload = session.payload
		self.slots = session.slots
		self.slotsAsObjects = session.slotsAsObjects
		self.customData = session.customData
		self.user = session.user
		self.message = session.message
		self.intentName = message.topic
		self.intentName = session.intentName
		self.intentHistory = session.intentHistory
		self.intentFilter = session.intentFilter
		self.notUnderstood = session.notUnderstood
		self.currentState = session.currentState


	def slotValue(self, slotName: str, index: int = 0, defaultValue: Any = None) -> Any:
		"""
		This returns the slot master value, not what was heard / captured
		"""
		try:
			return self.slotsAsObjects[slotName][index].value['value']
		except KeyError:
			return defaultValue


	def slotRawValue(self, slotName: str) -> str:
		"""
		This returns the slot raw value, what whas really heard / captured, so it can be a synonym for example
		"""
		return self.slots.get(slotName, '')


	def addToHistory(self, intent: Intent):
		self.intentHistory.append(intent)


	@property
	def previousIntent(self) -> Optional[Intent]:
		return self.intentHistory[-1] if self.intentHistory else None
