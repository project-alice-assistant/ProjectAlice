from datetime import datetime

from core.base.SuperManager import SuperManager
from core.base.model.Manager import Manager


class TimeManager(Manager):

	NAME = 'TimeManager'

	def __init__(self):
		super().__init__(self.NAME)

		self._fullMinuteTimer 	= None
		self._fiveMinuteTimer 	= None
		self._quarterHourTimer 	= None
		self._fullHourTimer 	= None


	def onBooted(self):
		self.onFullMinute()
		self.onFiveMinute()
		self.onQuarterHour()
		self.onFullHour()


	def onFullMinute(self):
		if self._fullMinuteTimer:
			SuperManager.getInstance().broadcast('onFullMinute', exceptions=[self.NAME], propagateToModules=True)

		second = int(datetime.now().strftime('%S'))
		secondsTillFullMinute = 60 - second
		self._fullMinuteTimer = self.ThreadManager.newTimer(secondsTillFullMinute, self.onFullMinute)


	def onFiveMinute(self):
		if self._fiveMinuteTimer:
			SuperManager.getInstance().broadcast('onFiveMinute', exceptions=[self.NAME], propagateToModules=True)

		minute = int(datetime.now().strftime('%M'))
		second = int(datetime.now().strftime('%S'))
		secondsTillFive = 60 * (round(300 / 60) - (minute % round(300 / 60))) - second

		self._fiveMinuteTimer = self.ThreadManager.newTimer(secondsTillFive, self.onFiveMinute)


	def onQuarterHour(self):
		if self._quarterHourTimer:
			SuperManager.getInstance().broadcast('onQuarterHour', exceptions=[self.NAME], propagateToModules=True)

		minute = int(datetime.now().strftime('%M'))
		second = int(datetime.now().strftime('%S'))
		secondsTillQuarter = 60 * (round(900 / 60) - (minute % round(900 / 60))) - second

		self._quarterHourTimer = self.ThreadManager.newTimer(secondsTillQuarter, self.onQuarterHour)


	def onFullHour(self):
		if self._fullHourTimer:
			SuperManager.getInstance().broadcast('onFullHour', exceptions=[self.NAME], propagateToModules=True)

		minute = int(datetime.now().strftime('%M'))
		second = int(datetime.now().strftime('%S'))

		secondsTillFullHour = ((60 - minute) * 60) - second
		self._fullHourTimer = self.ThreadManager.newTimer(secondsTillFullHour, self.onFullHour)
