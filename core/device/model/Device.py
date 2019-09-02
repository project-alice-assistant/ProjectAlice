class Device:
	def __init__(self, data: dict, connected: bool = False):
		self._id 			= data['id']
		self._deviceType	= data['type']
		self._uid 			= data['uid']
		self._room 			= data['room']
		self._name 			= ''
		self._connected 	= connected
		self._lastContact 	= 0


	@property
	def id(self) -> int:
		return self._id


	@property
	def deviceType(self) -> str:
		return self._deviceType


	@property
	def uid(self) -> str:
		return self._uid


	@property
	def room(self) -> str:
		return self._room


	@property
	def name(self) -> str:
		return self._name


	@name.setter
	def name(self, value: str):
		self._name = value


	@property
	def connected(self) -> bool:
		return self._connected


	@connected.setter
	def connected(self, value: bool):
		self._connected = value
