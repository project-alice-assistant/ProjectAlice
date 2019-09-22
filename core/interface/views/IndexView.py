from flask_classful import FlaskView, route
from flask import render_template

class IndexView(FlaskView):

	@route('/')
	@route('/home')
	@route('/index')
	@route('/start')
	def index(self):
		return render_template('home.html')