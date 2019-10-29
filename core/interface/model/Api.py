from flask_classful import FlaskView

from core.base.model.ProjectAliceObject import ProjectAliceObject


class Api(FlaskView, ProjectAliceObject):

	default_methods = ['GET', 'POST', 'PUT', 'DELETE']

	def __init__(self):
		super().__init__(logDepth=6)
