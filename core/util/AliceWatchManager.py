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


	def publish(self, payload: dict = None):
		topic = f'projectalice/logging/alicewatch'
		payload['text'] = f'![Orange]([{datetime.strftime(datetime.now(), "%H:%M:%S")}]) {payload["text"]}'

		self.MqttManager.publish(topic=topic, payload=payload)
