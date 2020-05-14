from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants


class WakewordEngine(ProjectAliceObject):

	NAME = constants.UNKNOWN

	def __init__(self):
		super().__init__()


	def onStart(self):
		self.logInfo(f'Starting **{self.NAME}**')
