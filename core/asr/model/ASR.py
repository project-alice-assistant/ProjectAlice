from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.dialog.model.DialogSession import DialogSession


class ASR(ProjectAliceObject):

	def __init__(self):
		self._capableOfArbitraryCapture = False
		super().__init__()


	@property
	def capableOfArbitraryCapture(self) -> bool:
		return self._capableOfArbitraryCapture


	def onStartListening(self, session: DialogSession): return
