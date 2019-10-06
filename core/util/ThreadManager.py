import threading
from typing import Callable

from core.base.model.Manager import Manager
from core.util.model.AliceEvent import AliceEvent
from core.util.model.ThreadTimer import ThreadTimer


class ThreadManager(Manager):

	NAME = 'ThreadManager'

	def __init__(self):
		super().__init__(self.NAME)

		self._timers	= list()
		self._threads 	= dict()
		self._events 	= dict()


	def onStop(self):
		super().onStop()
		for timer in self._timers:
			if timer.timer.isAlive():
				timer.timer.cancel()

		for thread in self._threads.values():
			if thread.isAlive():
				thread.join(timeout=1)

		for event in self._events.values():
			event.clear()


	def onQuarterHour(self):
		i = 0
		for threadTimer in self._timers:
			if not threadTimer.timer.isAlive():
				self._timers.remove(threadTimer)
				i += 1
		self._logger.info(f'[{self.NAME}] Cleaned {i} dead timers')


	def newTimer(self, interval: float, func: str, args: list = None, autoStart: bool = True) -> threading.Timer:
		if not args:
			args = list()

		threadTimer = ThreadTimer(callback=func, args=args)
		t = threading.Timer(interval=interval, function=self.onTimerEnd, args=[threadTimer])
		t.daemon = True
		threadTimer.timer = t
		self._timers.append(threadTimer)

		if autoStart:
			t.start()

		return t


	def doLater(self, interval: float, func: str, args: list = None):
		if not args:
			args = list()
		self.newTimer(interval=interval, func=func, args=args)


	def onTimerEnd(self, t: ThreadTimer):
		t.callback(*t.args)
		self.removeTimer(t)


	def removeTimer(self, t: ThreadTimer):
		if t.timer.isAlive():
			t.timer.cancel()

		if t in self._timers:
			self._timers.remove(t)


	def newThread(self, name: str, target: Callable, args: list = None, kwargs: dict = None, autostart: bool = True) -> threading.Thread:
		if not args:
			args = list()

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
			for t in threading.enumerate():
				if t.name == name:
					thread = t

		if thread and thread.isAlive():
			thread.join(timeout=1)


	def isThreadAlive(self, name: str) -> bool:
		if name not in self._threads:
			for t in threading.enumerate():
				if t.name == name and t.isAlive():
					return True
		else:
			return self._threads[name].isAlive()


	def newEvent(self, name: str, onSetCallback: str = None, onClearCallback: str = None, *args: list) -> AliceEvent:
		if name not in self._events:
			self._events[name] = AliceEvent(name, onSetCallback, onClearCallback, args)

		return self._events[name]


	def getEvent(self, name: str) -> AliceEvent:
		return self._events.get(name, AliceEvent(name))
