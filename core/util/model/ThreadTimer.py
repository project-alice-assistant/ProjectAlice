class ThreadTimer(object):
	def __init__(self, callback, args):
		self._timer 	= None
		self._callback 	= callback
		self._args 		= args

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