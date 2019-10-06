class ThreadTimer:
	def __init__(self, callback: str, *args: tuple, **kwargs: dict):
		self._timer 	= None
		self._callback 	= callback
		self._args 		= args
		self._kwargs 	= kwargs

	@property
	def timer(self):
		return self._timer

	@timer.setter
	def timer(self, t):
		self._timer = t

	@property
	def callback(self):
		return self._callback

	@property
	def args(self):
		return self._args

	@property
	def kwargs(self):
		return self._kwargs