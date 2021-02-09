from datetime import datetime

from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class AliceWatchManager(Manager):

	def __init__(self):
		super().__init__()


	def onHotword(self, deviceUid: str, user: str = constants.UNKNOWN_USER):
		self.publish(payload={
			'text': f'Detected on device **{self.DeviceManager.getDevice(uid=deviceUid).displayName}**, for user **{user}**',
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
			'text': text,
			'component': 'Nlu',
			'verbosity': 1
		})


	def onSessionStarted(self, session: DialogSession):
		#todo @psycho - Some situations like self.ask() from gui (addUser) theres no session.deviceUid
		# which results in getMainDevice().uid being None. the below is a temp fix
		if not session.deviceUid:
			session.deviceUid = self.DeviceManager.getMainDevice().uid
		self.publish(payload={
			'text': f'Session with id "**{session.sessionId}**" was started on device **{self.DeviceManager.getDevice(uid=session.deviceUid).displayName}**',
			'component': 'Dialogue',
			'verbosity': 1
		})


	def onCaptured(self, session: DialogSession):
		self.publish(payload={
			'text': f'Captured text "![yellow]({session.payload["text"]})" in {round(session.payload["seconds"], 1)}s',
			'component': 'Asr',
			'verbosity': 1
		})


	def onPartialTextCaptured(self, session, text: str, likelihood: float, seconds: float):
		self.publish(payload={
			'text': f'Capturing text: "![yellow]({text})"',
			'component': 'Asr',
			'verbosity': 2
		})


	def onHotwordToggleOn(self, deviceUid: str, session: DialogSession):
		self.publish(payload={
			'text': f'Was asked to toggle itself **on** on device **{self.DeviceManager.getDevice(uid=deviceUid).displayName}**',
			'component': 'Hotword',
			'verbosity': 2
		})


	def onHotwordToggleOff(self, deviceUid: str, session: DialogSession):
		# todo Temp fix for dialogue view.
		# SiteId was causing issues by defaulting to "Test" in new interface
		if deviceUid == 'Test':
			deviceUid = self.DeviceManager.getMainDevice().uid
		self.publish(payload={
			'text'     : f'Was asked to toggle itself **off** on device **{self.DeviceManager.getDevice(uid=deviceUid).displayName}**',
			'component': 'Hotword',
			'verbosity': 2
		})


	def onStartListening(self, session):
		self.publish(payload={
			'text': f'Was asked to start listening on device **{self.DeviceManager.getDevice(uid=session.deviceUid).displayName}**',
			'component': 'Asr',
			'verbosity': 2
		})


	def onStopListening(self, session):
		self.publish(payload={
			'text': f'Was asked to stop listening on device **{self.DeviceManager.getDevice(uid=session.deviceUid).displayName}**',
			'component': 'Asr',
			'verbosity': 2
		})


	def onContinueSession(self, session):
		self.publish(payload={
			'text': f'Was asked to continue session with id "**{session.sessionId}**" by saying "![yellow]({session.text})"',
			'component': 'Dialogue',
			'verbosity': 1
		})


	def onEndSession(self, session: DialogSession, reason: str = 'nominal'):
		if 'text' in session.payload:
			self.publish(payload={
				'text': f'Was asked to end session with id "**{session.sessionId}**" by saying "![yellow]({session.payload["text"]})"',
				'component': 'Dialogue',
				'verbosity': 1
			})
		else:
			self.publish(payload={
				'text': f'Was asked to end session with id "**{session.sessionId}**" by without text!',
				'component': 'Dialogue',
				'verbosity': 1
			})


	def onSay(self, session: DialogSession):
		self.publish(payload={
			'text': f'Was asked to say "![yellow]({session.payload["text"]})"',
			'component': 'Tts',
			'verbosity': 1
		})


	def onIntentNotRecognized(self, session: DialogSession):
		self.publish(payload={
			'text': f'![red](Intent not recognized) for "![yellow]({session.text})"',
			'component': 'Nlu',
			'verbosity': 1
		})


	def onSessionEnded(self, session: DialogSession):
		#todo @psycho - Some situations like self.ask() from gui (addUser) theres no session.deviceUid
		# which results in getMainDevice().uid being None. the below is a temp fix
		if not session.deviceUid:
			session.deviceUid = self.DeviceManager.getMainDevice().uid
		text = f'Session with id "**{session.sessionId}**" was ended on device **{self.DeviceManager.getDevice(uid=session.deviceUid).displayName}**.'

		reason = session.payload['termination']['reason']
		if reason:
			if reason == 'abortedByUser':
				text = f'{text} The session was aborted by the user.'
			elif reason == 'timeout':
				text = f'{text} The session timed out because the ASR component did not respond in a timely manner. Please ensure that the Asr is started and running correctly.'
			elif reason == 'intentNotRecognized':
				text = f'{text} The session was ended because the platform didn\'t understand the user.'
			elif reason == 'error':
				text = f'{text} The session was ended because there was a platform error.'
			else:
				text = f'{text} The session ended as expected.'

		self.publish(payload={
			'text': text,
			'component': 'Dialogue',
			'verbosity': 1
		})


	def onVadUp(self, deviceUid: str):
		self.publish(payload={
			'text': f'Up on device **{self.DeviceManager.getDevice(uid=deviceUid).displayName}**',
			'component': 'Voice activity',
			'verbosity': 2
		})


	def onVadDown(self, deviceUid: str):
		self.publish(payload={
			'text': f'Down on device **{self.DeviceManager.getDevice(uid=deviceUid).displayName}**',
			'component': 'Voice activity',
			'verbosity': 2
		})


	# TODO Should support site configuration
	def onConfigureIntent(self, intents: list):
		text = f'Was asked to configure all devices:'
		for intent in intents:  # NOSONAR
			text = f'{text}\n[=>]{"![green](enable)" if intent["enable"] else "![red](disable)"} {intent["intentId"]}'

		text = f'{text}'

		self.publish(payload={
			'text': text,
			'component': 'Dialogue',
			'verbosity': 1
		})


	def onNluQuery(self, session):
		self.publish(payload={
			'text': f'Was asked to parse input "![yellow]({session.payload.get("input", "")}")',
			'component': 'Nlu',
			'verbosity': 2
		})


	def publish(self, payload: dict = None):
		topic = f'projectalice/logging/alicewatch'
		payload['time'] = datetime.strftime(datetime.now(), '%H:%M:%S')

		self.MqttManager.publish(topic=topic, payload=payload)
