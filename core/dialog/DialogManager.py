from core.base.model.Manager import Manager


class DialogManager(Manager):
	NAME = 'DialogManager'


	def __init__(self):
		super().__init__(self.NAME)
