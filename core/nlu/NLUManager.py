from core.base.model.Manager import Manager


class NLUManager(Manager):
	NAME = 'NLUManager'


	def __init__(self):
		super().__init__(self.NAME)
