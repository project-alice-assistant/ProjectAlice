# -*- coding: utf-8 -*-

from datetime import datetime

import core.base.Managers as managers
from core.base.Manager import Manager


class TimeManager(Manager):

	NAME = 'TimeManager'

	def __init__(self, mainClass):
		super().__init__(mainClass, self.NAME)

		managers.TimeManager 	= self
		self._fullMinuteTimer 	= None
		self._fiveMinuteTimer 	= None
		self._quarterHourTimer 	= None
		self._fullHourTimer 	= None


	def onStart(self):
		super().onStart()
		self.onFullMinute()
		self.onFiveMinute()
		self.onQuarterHour()
		self.onFullHour()


	def onFullMinute(self):
		if self._fullMinuteTimer:
			managers.ModuleManager.broadcast('onFullMinute')
			managers.broadcast('onFullMinute', exceptions=[self.NAME])

		second = int(datetime.now().strftime('%S'))
		secondsTillFullMinute = 60 - second
		self._fullMinuteTimer = managers.ThreadManager.newTimer(secondsTillFullMinute, self.onFullMinute)


	def onFiveMinute(self):
		if self._fiveMinuteTimer:
			managers.ModuleManager.broadcast('onFiveMinute')
			managers.broadcast('onFiveMinute', exceptions=[self.NAME])

		minute = int(datetime.now().strftime('%M'))
		second = int(datetime.now().strftime('%S'))
		secondsTillFive = 60 * (round(300 / 60) - (minute % round(300 / 60))) - second

		self._fiveMinuteTimer = managers.ThreadManager.newTimer(secondsTillFive, self.onFiveMinute)


	def onQuarterHour(self):
		if self._quarterHourTimer:
			managers.ModuleManager.broadcast('onQuarterHour')
			managers.broadcast('onQuarterHour', exceptions=[self.NAME])

		minute = int(datetime.now().strftime('%M'))
		second = int(datetime.now().strftime('%S'))
		secondsTillQuarter = 60 * (round(900 / 60) - (minute % round(900 / 60))) - second

		self._quarterHourTimer = managers.ThreadManager.newTimer(secondsTillQuarter, self.onQuarterHour)


	def onFullHour(self):
		if self._fullHourTimer:
			managers.ModuleManager.broadcast('onFullHour')
			managers.broadcast('onFullHour', exceptions=[self.NAME])

		minute = int(datetime.now().strftime('%M'))
		second = int(datetime.now().strftime('%S'))

		secondsTillFullHour = ((60 - minute) * 60) - second
		self._fullHourTimer = managers.ThreadManager.newTimer(secondsTillFullHour, self.onFullHour)
