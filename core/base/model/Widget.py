import sqlite3

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.base.model.WidgetSizes import WidgetSizes


class Widget(ProjectAliceObject):
	DEFAULT_SIZE = WidgetSizes.w

	def __init__(self, data: sqlite3.Row):
		super().__init__()
