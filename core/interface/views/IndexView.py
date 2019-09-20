from flask_classful import FlaskView
from flask import render_template

class IndexView(FlaskView):
	route_base = '/'

	def index(self):
		return ''