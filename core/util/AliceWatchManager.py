from datetime import datetime

from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession


class AliceWatchManager(Manager):

	def __init__(self):
		super().__init__()
		self._verbosity = 0


	@property
	def verbosity(self):
		return self._verbosity


	@verbosity.setter
	def verbosity(self, value: int):
		self._verbosity = self.Commons.clamp(value, 0, 4)


	def onHotword(self, siteId: str, user: str = constants.UNKNOWN_USER):
		if self._verbosity < 1:
			return

		self.publish(payload={
			'text': f'[Hotword] Detected on site **{siteId}**, for user **{user}**'
		})


	def onIntent(self, session: DialogSession):
		text = f'[Dialogue] New intent detected ![Yellow]({session.payload["intent"]["intentName"]}) with confidence ![Yellow]({round(session.payload["intent"]["confidenceScore"], 3)})'

		if session.slots:
			text = f'{text}\n**__Slots__**'

			for slot in session.slots:
				text = f'{text}\n![Blue]({slot}) ![Yellow](->) {session.slotValue(slotName=slot, defaultValue="")}'
			text = f'{text}'

		self.publish(payload={
			'text': text
		})


	def onIntentParsed(self, session: DialogSession):
		if self._verbosity < 1:
			return

		text = f'[Nlu] Intent detected ![Yellow]({session.payload["intent"]["intentName"]}) with confidence **{round(session.payload["intent"]["confidenceScore"], 3)}** for input "![Yellow]({session.payload.get("input", "")})"'

		if session.slots:
			text = f'{text}\n**__Slots__**'

			for slot in session.slots:
				text = f'{text}\n![Blue]({slot}) ![Yellow](->) {session.slotValue(slotName=slot, defaultValue="")}'
			text = f'{text}'

		self.publish(payload={
			'text': text
		})


	def onSessionStarted(self, session: DialogSession):
		if self._verbosity < 1:
			return

		self.publish(payload={
			'text': f'[Dialogue] Session with id "**{session.sessionId}**" was started on site **{session.siteId}**'
		})


	def onCaptured(self, session: DialogSession):
		if self._verbosity < 1:
			return

		self.publish(payload={
			'text': f'[Asr] Captured text "![Yellow]({session.payload["text"]})" in {round(session.payload["seconds"], 1)}s'
		})


	def onPartialTextCaptured(self, session, text: str, likelihood: float, seconds: float):
		if self._verbosity < 2:
			return

		self.publish(payload={
			'text': f'[Asr] Capturing text: "![Yellow]({text})"'
		})


	def onHotwordToggleOn(self, siteId: str, session: DialogSession):
		if self._verbosity < 2:
			return

		self.publish(payload={
			'text': f'[Hotword] Was asked to toggle itself **on** on site **{siteId}**'
		})


	def onHotwordToggleOff(self, siteId: str, session: DialogSession):
		if self._verbosity < 2:
			return

		self.publish(payload={
			'text': f'[Hotword] Was asked to toggle itself **off** on site **{siteId}**'
		})


	def onStartListening(self, session):
		if self._verbosity < 2:
			return

		self.publish(payload={
			'text': f'[Asr] Was asked to start listening on site **{session.siteId}**'
		})


	def onStopListening(self, session):
		if self._verbosity < 2:
			return

		self.publish(payload={
			'text': f'[Asr] Was asked to stop listening on site **{session.siteId}**'
		})


	def onContinueSession(self, session):
		if self._verbosity < 1:
			return

		self.publish(payload={
			'text': f'[Dialogue] Was asked to continue session with id "**{session.sessionId}**" by saying "![Yellow]({session.text})"'
		})


	def onEndSession(self, session: DialogSession, reason: str = 'nominal'):
		if self._verbosity < 1:
			return

		self.publish(payload={
			'text': f'[Dialogue] Was asked to end session with id "**{session.sessionId}**" by saying "![Yellow]({session.payload["text"]})"'
		})


	def onSay(self, session: DialogSession):
		if self._verbosity < 1:
			return

		self.publish(payload={
			'text': f'[Tts] Was asked to say "![Yellow]({session.payload["text"]})"'
		})


	def onIntentNotRecognized(self, session: DialogSession):
		if self._verbosity < 1:
			return

		self.publish(payload={
			'text': f'[NLU] ![Red](Intent not recognized) for "![Yellow]({session.text})"'
		})


	def onSessionEnded(self, session: DialogSession):
		if self._verbosity < 1:
			return

		text = f'[Dialogue] Session with id "**{session.sessionId}**" was ended on site **{session.siteId}**.'

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
			'text': text
		})


	def onVadUp(self, siteId: str):
		if self._verbosity < 2:
			return

		self.publish(payload={
			'text': f'[VoiceActivity] Up on site **{siteId}**'
		})


	def onVadDown(self, siteId: str):
		if self._verbosity < 2:
			return

		self.publish(payload={
			'text': f'[VoiceActivity] Down on site **{siteId}**'
		})


	# TODO Should support site configuration
	def onConfigureIntent(self, intents: list):
		if self._verbosity < 1:
			return

		text = f'[Dialogue] Was asked to configure all sites:'
		for intent in intents: #NOSONAR
			text = f'{text}\n{"![Green](enable)" if intent["enable"] else "![Red](disable)"} {intent["intentId"]}'

		text = f'{text}'

		self.publish(payload={
			'text': text
		})


	def onNluQuery(self, session):
		if self._verbosity < 2:
			return

		self.publish(payload={
			'text': f'[Nlu] Was asked to parse input "![Yellow]({session.payload.get("input", "")}")'
		})


	def publish(self, payload: dict = None):
		topic = f'projectalice/logging/alicewatch'
		payload['text'] = f'![Yellow]([{datetime.strftime(datetime.now(), "%H:%M:%S")}]) {payload["text"]}'

		self.MqttManager.publish(topic=topic, payload=payload)
