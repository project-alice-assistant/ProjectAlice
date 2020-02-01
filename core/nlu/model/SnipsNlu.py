from core.dialog.model.DialogSession import DialogSession
from core.nlu.model.NluEngine import NluEngine


class SnipsNlu(NluEngine):
	NAME = 'Snips NLU'


	def __init__(self):
		super().__init__()


	def onNluQuery(self, session: DialogSession):
		pass
