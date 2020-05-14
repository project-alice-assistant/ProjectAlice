from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants


class WakewordEngine(ProjectAliceObject):

	NAME = constants.UNKNOWN

	def __init__(self):
		super().__init__()
		self._enabled = True


	def onStart(self):
		self.logInfo(f'Starting **{self.NAME}**')
		self._enabled = True


	def onStop(self, **kwargs):
		self._enabled = False


	@property
	def enabled(self) -> bool:
		return self._enabled


	@enabled.setter
	def enabled(self, value: bool):
		self._enabled = value
