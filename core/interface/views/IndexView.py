from flask import render_template
from flask_classful import route

from core.interface.views.View import View


class IndexView(View):

	def __init__(self):
		super().__init__()

	@route('/')
	@route('/home')
	@route('/index')
	@route('/start')
	def index(self):
		return render_template('home.html', langData=self._langData)