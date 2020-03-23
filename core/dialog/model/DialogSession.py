from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from paho.mqtt.client import MQTTMessage

from core.base.SuperManager import SuperManager
from core.base.model import Intent
from core.commons import constants


@dataclass
class DialogSession:
	siteId: str
	sessionId: str = ''
	user: str = constants.UNKNOWN_USER
	message: MQTTMessage = None
	intentName: str = ''
	notUnderstood: int = 0
	currentState: str = constants.DEFAULT
	isAPIGenerated: bool = False
	hasEnded: bool = False
	probabilityThreshold: float = 0.5
	slots: dict = field(default_factory=dict)
	slotsAsObjects: dict = field(default_factory=dict)
	customData: dict = field(default_factory=dict)
	payload: dict = field(default_factory=dict)
	intentHistory: list = field(default_factory=list)
	intentFilter: list = field(default_factory=list)


	def __post_init__(self):
		self.probabilityThreshold = SuperManager.getInstance().configManager.getAliceConfigByName('probabilityThreshold')


	def extend(self, message: MQTTMessage, sessionId: str = None):
		if sessionId:
			self.sessionId = sessionId

		self.addToHistory(self.intentName)

		commonsManager = SuperManager.getInstance().commonsManager
		self.message = message
		self.intentName = message.topic
		self.payload = commonsManager.payload(message)
		self.slots = commonsManager.parseSlots(message)
		self.slotsAsObjects = commonsManager.parseSlotsToObjects(message)
		self.customData = commonsManager.parseCustomData(message)


	def update(self, message: MQTTMessage):
		self.addToHistory(self.intentName)

		commonsManager = SuperManager.getInstance().commonsManager
		self.message = message
		self.intentName = message.topic
		self.payload = commonsManager.payload(message)
		self.slots.update(commonsManager.parseSlots(message))
		self.slotsAsObjects.update(commonsManager.parseSlotsToObjects(message))

		if self.customData:
			self.customData.update(commonsManager.parseCustomData(message))
		else:
			self.customData = dict()


	def reviveOldSession(self, session: DialogSession):
		"""
		Revives old session keeping siteId, sessionId and isAPIGenerated from the
		new session
		"""
		self.addToHistory(self.intentName)

		self.payload = session.payload
		self.slots = session.slots
		self.slotsAsObjects = session.slotsAsObjects
		self.customData = session.customData
		self.user = session.user
		self.message = session.message
		self.intentName = session.intentName
		self.intentHistory = session.intentHistory
		self.intentFilter = session.intentFilter
		self.notUnderstood = session.notUnderstood
		self.currentState = session.currentState
		self.isAPIGenerated = session.isAPIGenerated
		self.probabilityThreshold = session.probabilityThreshold


	def slotValue(self, slotName: str, index: int = 0, defaultValue: Any = None) -> Any:
		"""
		This returns the slot master value, not what was heard / captured
		"""
		try:
			return self.slotsAsObjects[slotName][index].value['value']
		except (KeyError, IndexError):
			return defaultValue


	def slotRawValue(self, slotName: str) -> str:
		"""
		This returns the slot raw value, what was really heard / captured, so it can be a synonym for example
		"""
		return self.slots.get(slotName, '')


	def addToHistory(self, intent: Intent):
		self.intentHistory.append(intent)


	@property
	def previousIntent(self) -> Optional[Intent]:
		return self.intentHistory[-1] if self.intentHistory else None
