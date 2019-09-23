from flask_classful import FlaskView, route
from flask import render_template

class AdminView(FlaskView):

	def index(self):
		return render_template('admin.html')