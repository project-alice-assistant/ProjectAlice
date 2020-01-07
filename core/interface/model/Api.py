from flask_classful import FlaskView

from core.base.model.ProjectAliceObject import ProjectAliceObject


class Api(FlaskView, ProjectAliceObject):
	default_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
	_version = '1.0.1'


	def __init__(self):
		super().__init__(logDepth=6)


	@classmethod
	def version(cls) -> str:
		return f'v{cls._version}'
