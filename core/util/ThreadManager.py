import threading
from typing import Callable

from core.base.model.Manager import Manager
from core.util.model.AliceEvent import AliceEvent
from core.util.model.ThreadTimer import ThreadTimer


class ThreadManager(Manager):

	def __init__(self):
		super().__init__()

		self._timers = list()
		self._threads = dict()
		self._events = dict()


	def onStop(self):
		super().onStop()
		for timer in self._timers:
			if timer.timer.isAlive():
				timer.timer.cancel()

		for thread in self._threads.values():
			if thread.isAlive():
				thread.join(timeout=1)

		for event in self._events.values():
			if event.isSet():
				event.clear()


	def onQuarterHour(self):
		deadTimers = 0
		for threadTimer in self._timers:
			if not threadTimer.timer.isAlive():
				self._timers.remove(threadTimer)
				deadTimers += 1
		self.logInfo(f'Cleaned {deadTimers} dead timers')


	def newTimer(self, interval: float, func: Callable, autoStart: bool = True, args: list = None, kwargs: dict = None) -> threading.Timer:
		args = args or list()
		kwargs = kwargs or dict()

		threadTimer = ThreadTimer(callback=func, args=args, kwargs=kwargs)
		timer = threading.Timer(interval=interval, function=self.onTimerEnd, args=[threadTimer])
		timer.daemon = True
		threadTimer.timer = timer
		self._timers.append(threadTimer)

		if autoStart:
			timer.start()

		return timer


	def doLater(self, interval: float, func: Callable, args: list = None, kwargs: dict = None):
		self.newTimer(interval=interval, func=func, args=args, kwargs=kwargs)


	def onTimerEnd(self, timer: ThreadTimer):
		if not timer or not timer.callback:
			return

		timer.callback(*timer.args, **timer.kwargs)
		self.removeTimer(timer)


	def removeTimer(self, timer: ThreadTimer):
		if not timer or not timer.callback:
			return

		if timer.timer.is_alive():
			timer.timer.cancel()

		if timer in self._timers:
			self._timers.remove(timer)


	def newThread(self, name: str, target: Callable, autostart: bool = True, args: list = None, kwargs: dict = None) -> threading.Thread:
		args = args or list()
		kwargs = kwargs or dict()

		if name in self._threads:
			self._threads[name].join(timeout=2)

		thread = threading.Thread(name=name, target=target, args=args, kwargs=kwargs)
		thread.setDaemon(True)

		if autostart:
			thread.start()

		self._threads[name] = thread
		return thread


	def terminateThread(self, name: str):
		thread = self._threads.pop(name, None)
		if not thread:
			for aThread in threading.enumerate():
				if aThread.name == name:
					thread = aThread

		if thread and thread.is_alive():
			thread.join(timeout=1)


	def isThreadAlive(self, name: str) -> bool:
		if name not in self._threads:
			return any(t.name == name and t.is_alive() for t in threading.enumerate())

		return self._threads[name].isAlive()


	def newEvent(self, name: str, onSetCallback: str = None, onClearCallback: str = None) -> AliceEvent:
		if name in self._events:
			self._events[name].clear()

		self._events[name] = AliceEvent(name, onSetCallback, onClearCallback)
		return self._events[name]


	def getEvent(self, name: str) -> AliceEvent:
		return self._events.get(name, AliceEvent(name))


	def clearEvent(self, name: str):
		if name in self._events:
			self._events.pop(name).clear()
