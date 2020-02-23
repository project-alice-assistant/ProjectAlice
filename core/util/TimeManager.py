from datetime import datetime

from core.base.model.Manager import Manager
from core.commons import constants


class TimeManager(Manager):

	def __init__(self):
		super().__init__()


	def onBooted(self):
		self.timerSignal(1, constants.EVENT_FULL_MINUTE)
		self.timerSignal(5, constants.EVENT_FIVE_MINUTE)
		self.timerSignal(15, constants.EVENT_QUARTER_HOUR)
		self.timerSignal(60, constants.EVENT_FULL_HOUR)


	def timerSignal(self, minutes: int, signal: str, running: bool = False):
		if running:
			self.broadcast(signal, exceptions=[self.name], propagateToSkills=True)

		minute = datetime.now().minute
		second = datetime.now().second
		missingSeconds = 60 * (minutes - minute % minutes) - second
		self.ThreadManager.doLater(interval=missingSeconds, func=self.timerSignal, args=[minutes, signal, True])
