from core.base.model.Manager import Manager


class AudioServer(Manager):
	NAME = 'AudioServer'


	def __init__(self):
		super().__init__(self.NAME)
