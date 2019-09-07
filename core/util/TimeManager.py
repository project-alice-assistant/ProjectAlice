from datetime import datetime

from core.base.Manager import Manager
from core.base.SuperManager import SuperManager


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
			SuperManager.getInstance().moduleManager.broadcast('onFullMinute')
			SuperManager.getInstance().broadcast('onFullMinute', exceptions=[self.NAME])

		second = int(datetime.now().strftime('%S'))
		secondsTillFullMinute = 60 - second
		self._fullMinuteTimer = SuperManager.getInstance().threadManager.newTimer(secondsTillFullMinute, self.onFullMinute)


	def onFiveMinute(self):
		if self._fiveMinuteTimer:
			SuperManager.getInstance().moduleManager.broadcast('onFiveMinute')
			SuperManager.getInstance().broadcast('onFiveMinute', exceptions=[self.NAME])

		minute = int(datetime.now().strftime('%M'))
		second = int(datetime.now().strftime('%S'))
		secondsTillFive = 60 * (round(300 / 60) - (minute % round(300 / 60))) - second

		self._fiveMinuteTimer = SuperManager.getInstance().threadManager.newTimer(secondsTillFive, self.onFiveMinute)


	def onQuarterHour(self):
		if self._quarterHourTimer:
			SuperManager.getInstance().moduleManager.broadcast('onQuarterHour')
			SuperManager.getInstance().broadcast('onQuarterHour', exceptions=[self.NAME])

		minute = int(datetime.now().strftime('%M'))
		second = int(datetime.now().strftime('%S'))
		secondsTillQuarter = 60 * (round(900 / 60) - (minute % round(900 / 60))) - second

		self._quarterHourTimer = SuperManager.getInstance().threadManager.newTimer(secondsTillQuarter, self.onQuarterHour)


	def onFullHour(self):
		if self._fullHourTimer:
			SuperManager.getInstance().moduleManager.broadcast('onFullHour')
			SuperManager.getInstance().broadcast('onFullHour', exceptions=[self.NAME])

		minute = int(datetime.now().strftime('%M'))
		second = int(datetime.now().strftime('%S'))

		secondsTillFullHour = ((60 - minute) * 60) - second
		self._fullHourTimer = SuperManager.getInstance().threadManager.newTimer(secondsTillFullHour, self.onFullHour)
