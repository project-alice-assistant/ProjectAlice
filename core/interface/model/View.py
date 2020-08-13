from flask_classful import FlaskView

from core.base.model.ProjectAliceObject import ProjectAliceObject


class View(FlaskView, ProjectAliceObject):

	default_methods = ['POST']

	def __init__(self):
		super().__init__()
		self._langData = self.WebInterfaceManager.langData
