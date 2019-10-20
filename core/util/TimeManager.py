from datetime import datetime

from core.base.model.Manager import Manager


class TimeManager(Manager):

	NAME = 'TimeManager'

	def __init__(self):
		super().__init__(self.NAME)


	def onBooted(self):
		self.timerSignal(1, 'onFullMinute')
		self.timerSignal(5, 'onFiveMinute')
		self.timerSignal(15, 'onQuarterHour')
		self.timerSignal(60, 'onFullHour')


	def timerSignal(self, minutes: int, signal: str, running: bool = False):
		if running:
			self.broadcast(signal, exceptions=[self.NAME], propagateToModules=True)

		minute = datetime.now().minute
		second = datetime.now().second
		missingSeconds = 60 * (minutes - minute % minutes) - second
		self.ThreadManager.doLater(interval=missingSeconds, func=self.timerSignal, args=[minutes, signal, True])
