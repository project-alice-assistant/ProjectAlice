from core.base.model.Manager import Manager


class HotwordManager(Manager):
	NAME = 'HotwordManager'


	def __init__(self):
		super().__init__(self.NAME)
