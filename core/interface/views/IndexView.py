from flask_classful import FlaskView, route

class IndexView(FlaskView):

	@route('/')
	@route('/home')
	@route('/index')
	@route('/start')
	def index(self):
		return ''