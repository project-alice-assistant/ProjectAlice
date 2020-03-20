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


	def onIntentParsed(self, session: DialogSession):
		self.publish(payload={
			'text': f'[Dialogue] New intent detected ![Yellow]({session.payload["intent"]["intentName"]}) with confidence ![Yellow]({round(session.payload["intent"]["confidenceScore"], 3)})'
		})


	def onSessionStarted(self, session: DialogSession):
		if self._verbosity < 1:
			return

		self.publish(payload={
			'text': f'[Dialogue] Session with id "**{session.sessionId}**" was started on site **office**'
		})


	def onCaptured(self, session: DialogSession):
		if self._verbosity < 1:
			return

		self.publish(payload={
			'text': f'[ASR] Captured text "![Yellow]({session.payload["text"]})" in {round(session.payload["seconds"], 1)}s'
		})


	def onEndSession(self, session: DialogSession):
		if self._verbosity < 1:
			return

		self.publish(payload={
			'text': f'[Dialogue] Was asked to end session with id "**{session.sessionId}**" by saying "{session.payload["text"]}"'
		})


	def onSay(self, session: DialogSession):
		if self._verbosity < 1:
			return

		self.publish(payload={
			'text': f'[TTS] Was asked to say "![Yellow]({session.payload["text"]})"'
		})


	def onSessionEnded(self, session: DialogSession):
		if self._verbosity < 1:
			return

		self.publish(payload={
			'text': f'[Dialogue] Session with id "**{session.sessionId}**" was ended on site **{session.siteId}**. The session ended as expected'
		})


	def publish(self, payload: dict = None):
		topic = f'projectalice/logging/alicewatch'
		payload['text'] = f'![Orange]([{datetime.strftime(datetime.now(), "%H:%M:%S")}]) {payload["text"]}'

		self.MqttManager.publish(topic=topic, payload=payload)
