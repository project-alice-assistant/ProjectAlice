import sqlite3

from core.base.model.Widget import Widget


class Date(Widget):

	SIZE = 'w_small_wide'
	OPTIONS = dict()

	def __init__(self, data: sqlite3.Row):
		super().__init__(data)