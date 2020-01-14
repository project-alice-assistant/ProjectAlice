import attr


@attr.s(slots=True, frozen=True)
class Slot:
	data = attr.ib()
	slotName = attr.ib(init=False)
	entity = attr.ib(init=False)
	rawValue = attr.ib(init=False)
	value = attr.ib(init=False)
	range = attr.ib(init=False)


	def __attrs_post_init__(self):
		super().__setattr__('slotName', self.data['slotName'])
		super().__setattr__('entity', self.data['entity'])
		super().__setattr__('rawValue', self.data['rawValue'])
		super().__setattr__('value', self.data['value'])
		super().__setattr__('range', self.data['range'])
