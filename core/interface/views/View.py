from flask_classful import FlaskView

from core.base.model.ProjectAliceObject import ProjectAliceObject


class View(FlaskView, ProjectAliceObject):

	def __init__(self):
		super().__init__(logDepth=6)
		self._langData = self.WebInterfaceManager.langData
