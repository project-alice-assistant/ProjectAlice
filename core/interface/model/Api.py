from flask_classful import FlaskView

from core.base.model.ProjectAliceObject import ProjectAliceObject


class Api(FlaskView, ProjectAliceObject):

	default_methods = ['GET', 'POST', 'PUT', 'DELETE']
	_version = '1.0.0'

	def __init__(self):
		super().__init__(logDepth=6)


	@classmethod
	def version(cls) -> str:
		return f'v{cls._version}'
