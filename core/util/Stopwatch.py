import time


class Stopwatch:
	def __init__(self, precision: int = 2):
		self._startTime = None
		self._time = None
		self._precision = precision


	@property
	def time(self) -> int:
		if self._time:
			return self._time
		elif self._startTime:
			return time.time() - self._startTime
		else:
			return 0


	def start(self):
		self._startTime = time.time()


	def lap(self) -> float:
		currentTime = time.time()
		startTime = self._startTime
		self._startTime = currentTime
		return currentTime - startTime


	def stop(self) -> int:
		self._time = time.time() - self._startTime
		return self._time


	def __enter__(self):
		self.start()
		return self


	def __exit__(self, tpe, value, tb):
		self.stop()


	def __str__(self) -> str:
		return f'{self.time:.{self._precision}f}'
