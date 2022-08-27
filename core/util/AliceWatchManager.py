#  Copyright (c) 2021
#
#  This file, AliceWatchManager.py, is part of Project Alice.
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
#  Last modified: 2021.04.24 at 12:56:47 CEST

from datetime import datetime

from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class AliceWatchManager(Manager):

	def __init__(self):
		super().__init__()


	def onHotword(self, deviceUid: str, user: str = constants.UNKNOWN_USER):
		self.publish(payload={
			'text'     : f'Detected on device **{self.getDisplayName(deviceUid)}**, for user **{user}**',
			'component': 'Hotword',
			'verbosity': 1
		})


	def onIntent(self, session: DialogSession):
		text = f'New intent detected ![yellow]({session.payload["intent"]["intentName"]}) with confidence ![yellow]({round(session.payload["intent"]["confidenceScore"], 3)})'

		if session.slots:
			text = f'{text}\n**__Slots__**'

			for slot in session.slots:
				text = f'{text}\n![blue]({slot}) ![yellow](->) {session.slotValue(slotName=slot, defaultValue="")}'
			text = f'{text}'

		self.publish(payload={
			'text'     : text,
			'component': 'Dialogue',
			'verbosity': 0
		})


	def onIntentParsed(self, session: DialogSession):
		text = f'Intent detected ![yellow]({session.payload["intent"]["intentName"]}) with confidence **{round(session.payload["intent"]["confidenceScore"], 3)}** for input "![yellow]({session.payload.get("input", "")})"'

		if session.slots:
			text = f'{text}\n**__Slots__**'

			for slot in session.slots:
				text = f'{text}\n![blue]({slot}) ![yellow](->) {session.slotValue(slotName=slot, defaultValue="")}'
			text = f'{text}'

		self.publish(payload={
			'text'     : text,
			'component': 'Nlu',
			'verbosity': 1
		})


	def onSessionStarted(self, session: DialogSession):
		if not session.deviceUid:
			session.deviceUid = self.DeviceManager.getMainDevice().uid

		self.publish(payload={
			'text'     : f'Session with id "**{session.sessionId}**" was started on device **{self.getDisplayName(session.deviceUid)}**',
			'component': 'Dialogue',
			'verbosity': 1
		})


	def onCaptured(self, session: DialogSession):
		self.publish(payload={
			'text'     : f'Captured text "![yellow]({session.payload["text"]})" in {round(session.payload["seconds"], 1)}s',
			'component': 'Asr',
			'verbosity': 1
		})


	def onPartialTextCaptured(self, session, text: str, likelihood: float, seconds: float):
		self.publish(payload={
			'text'     : f'Capturing text: "![yellow]({text})"',
			'component': 'Asr',
			'verbosity': 2
		})


	def onHotwordToggleOn(self, deviceUid: str):
		self.publish(payload={
			'text'     : f'Was asked to toggle itself **on** on device **{self.getDisplayName(deviceUid)}**',
			'component': 'Hotword',
			'verbosity': 2
		})


	def onHotwordToggleOff(self, deviceUid: str):
		self.publish(payload={
			'text'     : f'Was asked to toggle itself **off** on device **{self.getDisplayName(deviceUid)}**',
			'component': 'Hotword',
			'verbosity': 2
		})


	def onStartListening(self, session):
		self.publish(payload={
			'text'     : f'Was asked to start listening on device **{self.getDisplayName(session.deviceUid)}**',
			'component': 'Asr',
			'verbosity': 2
		})


	def onStopListening(self, session):
		self.publish(payload={
			'text'     : f'Was asked to stop listening on device **{self.getDisplayName(session.deviceUid)}**',
			'component': 'Asr',
			'verbosity': 2
		})


	def onContinueSession(self, session):
		self.publish(payload={
			'text'     : f'Was asked to continue session with id "**{session.sessionId}**" by saying "![yellow]({session.text})"',
			'component': 'Dialogue',
			'verbosity': 1
		})


	def onEndSession(self, session: DialogSession, reason: str = 'nominal'):
		if 'text' in session.payload:
			self.publish(payload={
				'text'     : f'Was asked to end session with id "**{session.sessionId}**" by saying "![yellow]({session.payload["text"]})"',
				'component': 'Dialogue',
				'verbosity': 1
			})
		else:
			self.publish(payload={
				'text'     : f'Was asked to end session with id "**{session.sessionId}**" by without text!',
				'component': 'Dialogue',
				'verbosity': 1
			})


	def onSay(self, session: DialogSession):
		self.publish(payload={
			'text'     : f'Was asked to say "![yellow]({session.payload["text"]})"',
			'component': 'Tts',
			'verbosity': 1
		})


	def onIntentNotRecognized(self, session: DialogSession):
		self.publish(payload={
			'text'     : f'![red](Intent not recognized) for "![yellow]({session.text})"',
			'component': 'Nlu',
			'verbosity': 1
		})


	def onSessionEnded(self, session: DialogSession):
		text = f'Session with id "**{session.sessionId}**" was ended on device **{self.getDisplayName(session.deviceUid)}**.'

		reason = session.payload['termination']['reason']
		if reason:
			if reason == 'abortedByUser':
				text = f'{text} The session was aborted by the user.'
			elif reason == 'timeout':
				text = f'{text} The session timed out because a component did not respond in a timely manner. Please ensure that the Asr is started and running correctly.'
			elif reason == 'intentNotRecognized':
				text = f'{text} The session was ended because the platform didn\'t understand the user.'
			elif reason == 'error':
				text = f'{text} The session was ended because there was a platform error.'
			else:
				text = f'{text} The session ended as expected.'

		self.publish(payload={
			'text'     : text,
			'component': 'Dialogue',
			'verbosity': 1
		})


	def onVadUp(self, deviceUid: str):
		self.publish(payload={
			'text'     : f'Up on device **{self.getDisplayName(deviceUid)}**',
			'component': 'Voice activity',
			'verbosity': 2
		})


	def onVadDown(self, deviceUid: str):
		self.publish(payload={
			'text'     : f'Down on device **{self.getDisplayName(deviceUid)}**',
			'component': 'Voice activity',
			'verbosity': 2
		})


	def onConfigureIntent(self, intents: list):
		text = f'Was asked to configure all devices:'
		for intent in intents:  # NOSONAR
			text = f'{text}\n[=>]{"![green](enable)" if intent["enable"] else "![red](disable)"} {intent["intentId"]}'

		text = f'{text}'

		self.publish(payload={
			'text'     : text,
			'component': 'Dialogue',
			'verbosity': 1
		})


	def onNluQuery(self, session):
		self.publish(payload={
			'text'     : f'Was asked to parse input "![yellow]({session.payload.get("input", "")}")',
			'component': 'Nlu',
			'verbosity': 2
		})


	def publish(self, payload: dict = None):
		topic = f'projectalice/logging/alicewatch'
		payload['time'] = datetime.strftime(datetime.now(), '%H:%M:%S')

		self.MqttManager.publish(topic=topic, payload=payload)


	def getDisplayName(self, deviceUid: str) -> str:
		"""
		This method should not be moved to DeviceManager or Device, as the output options are specific for AliceWatch
		Others need seperate handling
		:param deviceUid: The device uid to get the name from
		:return: device name
		"""
		device = self.DeviceManager.getDevice(uid=deviceUid)
		if device:
			return device.displayName
		else:
			return f'with unknown UID {deviceUid}'
