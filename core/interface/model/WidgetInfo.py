class WidgetInfo:

	def __init__(self, data: dict):
		self._name = data['name']
		self._parent = data['parent']
		self._x = data['posx']
		self._y = data['posy']
		self._state = True if int(data['state']) == 1 else False
		self._size = data['size']
		self._options = data['options']


	@property
	def parent(self) -> str:
		return self._parent


	@parent.setter
	def parent(self, value: str):
		self._parent = value


	@property
	def name(self) -> str:
		return self._name


	@name.setter
	def name(self, value: str):
		self._name = value


	@property
	def x(self) -> int:
		return self._x


	@x.setter
	def x(self, value: int):
		self._x = value


	@property
	def y(self) -> int:
		return self._y


	@y.setter
	def y(self, value: int):
		self._y = value


	@property
	def state(self) -> bool:
		return self._state == 1


	@state.setter
	def state(self, value: bool):
		self._state = 1 if value else 0


	@property
	def size(self) -> str:
		return self._size


	@size.setter
	def size(self, value: str):
		self._size = value


	@property
	def options(self) -> str:
		return self._options


	@options.setter
	def options(self, value: str):
		self._options = value


	def __repr__(self):
		return '---- WIDGET -----' + \
		       '\n Parent: ' + self.parent + \
		       '\n Name: ' + self.name + \
		       '\n Size: ' + self.size + \
		       '\n State: ' + str(self.state) + \
		       '\n PosX: ' + str(self.x) + \
		       '\n PosY: ' + str(self.y)