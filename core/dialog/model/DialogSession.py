#  Copyright (c) 2021
#
#  This file, DialogSession.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:46 CEST

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from paho.mqtt.client import MQTTMessage

from core.base.SuperManager import SuperManager
from core.base.model import Intent
from core.commons import constants


@dataclass
class DialogSession(object):
	deviceUid: str
	sessionId: str = ''
	increaseTimeout: int = 0
	user: str = constants.UNKNOWN_USER
	message: MQTTMessage = None
	intentName: str = ''
	notUnderstood: int = 0
	currentState: str = constants.DEFAULT

	# TODO rework with clear states
	hasEnded: bool = False
	hasStarted: bool = False
	isEnding: bool = False
	inDialog = False

	probabilityThreshold: float = 0.5
	text: str = ''
	input: str = ''
	previousInput: str = ''
	isNotification: bool = False
	slots: dict = field(default_factory=dict)
	slotsAsObjects: dict = field(default_factory=dict)
	customData: dict = field(default_factory=dict)
	payload: dict = field(default_factory=dict)
	intentHistory: list = field(default_factory=list)
	intentFilter: list = field(default_factory=list)
	textOnly: bool = False  # The session doesn't use audio, but text only. Per exemple, for Telegram messages sent to Alice
	textInput: bool = False  # The session is started, user side, by a text input, not with voice capture, like dialogview on web ui
	keptOpen: bool = False  # The session has ended, but is kept open for a new promt
	lastWasSoundPlayOnly: bool = False  # We don't use request ids for play bytes topic. Both say and playaudio use play bytes, therefor we need to track if the last play bytes was sound only or TTS
	locationId: int = -1  # Where this session is taking place
	init: dict = field(default_factory=dict)


	def __post_init__(self):  # NOSONAR
		self.probabilityThreshold = SuperManager.getInstance().ConfigManager.getAliceConfigByName('probabilityThreshold')


	def extend(self, message: MQTTMessage, sessionId: str = None):
		if sessionId:
			self.sessionId = sessionId

		self.addToHistory(self.intentName)

		commonsManager = SuperManager.getInstance().CommonsManager
		self.message = message
		self.intentName = message.topic
		self.payload = commonsManager.payload(message)
		self.slots = commonsManager.parseSlots(message)
		self.slotsAsObjects = commonsManager.parseSlotsToObjects(message)

		customData = commonsManager.parseCustomData(message)
		self.customData = {**self.customData, **customData}


	def update(self, message: MQTTMessage):
		self.addToHistory(self.intentName)

		commonsManager = SuperManager.getInstance().CommonsManager
		self.message = message
		self.intentName = message.topic
		self.payload = commonsManager.payload(message)

		if not isinstance(self.payload, dict):
			return

		self.slots.update(commonsManager.parseSlots(message))
		self.slotsAsObjects.update(commonsManager.parseSlotsToObjects(message))
		self.text = self.payload.get('text', '')
		self.input = self.payload.get('input', '')

		if message.topic == constants.TOPIC_END_SESSION:
			keepSessionOpen = SuperManager.getInstance().ConfigManager.getAliceConfigByName('keepSessionOpen')

			self.keptOpen = not self.payload.get('forceEnd', False) \
			                and ( keepSessionOpen == 'Always'
			                      or keepSessionOpen == 'Allowed' and self.payload.get('requestContinue', False) )

		customData = commonsManager.parseCustomData(message)
		self.customData = {**self.customData, **customData}

		deviceManager = SuperManager.getInstance().DeviceManager
		if deviceManager:
			device = deviceManager.getDevice(uid=self.deviceUid)
			if not device:
				return

			self.locationId = device.getLocation()


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
		if str(intent).startswith('hermes/intent'):
			self.intentHistory.append(intent)


	@property
	def previousIntent(self) -> Optional[str]:
		try:
			return str(self.intentHistory[-1])
		except:
			return None


	@property
	def secondLastIntent(self) -> Optional[str]:
		try:
			return str(self.intentHistory[-2])
		except:
			return None
