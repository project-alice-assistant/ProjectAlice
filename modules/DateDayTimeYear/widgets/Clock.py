import sqlite3

from core.base.model.Widget import Widget


class Clock(Widget):

	SIZE = 'w_small'
	OPTIONS = dict()

	def __init__(self, data: sqlite3.Row):
		super().__init__(data)