from flask import jsonify
from flask_classful import route

from core.webApi.model.Api import Api
from core.util.Decorators import ApiAuthenticated


class StateApi(Api):
	route_base = f'/api/{Api.version()}/state/'


	def __init__(self):
		super().__init__()
		self.default_methods = ['GET']


	@route('/<statePath>/', methods=['GET'])
	@ApiAuthenticated
	def get(self, statePath: str):
		try:
			state = self.StateManager.getState(statePath)
			if not state:
				raise Exception

			return jsonify(success=True, state=state.currentState.value)
		except:
			return jsonify(success=False, message=f'Unknown state: {statePath}')
