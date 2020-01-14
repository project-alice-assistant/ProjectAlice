import attr

@attr.s(slots=True, auto_attribs=True)
class Device:
	data: dict
	connected: bool = False
	name: str = ''
	lastContact: int = 0

	id: int = attr.ib(init=False)
	deviceType: str = attr.ib(init=False)
	uid: str = attr.ib(init=False)
	room: str = attr.ib(init=False)

	def __attrs_post_init__(self):
		self.id = self.data['id']
		self.deviceType = self.data['type']
		self.uid = self.data['uid']
		self.room = self.data['room']
