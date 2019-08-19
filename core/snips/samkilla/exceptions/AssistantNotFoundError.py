
class AssistantNotFoundError(Exception):

	def __init__(self, status, message, context):
		self._status = status
		self._message = message
		self._context = context
		super().__init__(message)

	@property
	def status(self):
		return self._status

	@property
	def message(self):
		return self._message

	@property
	def context(self):
		return self._context