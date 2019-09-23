from flask_classful import FlaskView

from core.base.SuperManager import SuperManager


class View(FlaskView):

	def __init__(self):
		super().__init__()
		self._langData = SuperManager.getInstance().webInterfaceManager.langData