class AssistantNotFoundError(Exception):

	def __init__(self, status, message, context):
		self._status = status
		self._message = message
		self._context = context
		super().__init__(message)


	@property
	def status(self) -> str:
		return self._status


	@property
	def message(self) -> str:
		return self._message


	@property
	def context(self) -> str:
		return self._context
