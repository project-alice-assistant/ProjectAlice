from flask_classful import FlaskView

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.commons import constants


class View(FlaskView, ProjectAliceObject):

	default_methods = ['POST']

	def __init__(self):
		super().__init__()

		self._everyPagesRenderValues = {
			'langData'     : self.WebInterfaceManager.langData,
			'aliceSettings': self.ConfigManager.aliceConfigurations,
			'aliceVersion' : constants.VERSION
		}
