from flask import jsonify
from flask_classful import route

from core.interface.model.Api import Api
from core.util.Decorators import ApiAuthenticated


class UtilsApi(Api):
	route_base = f'/api/{Api.version()}/utils/'


	def __init__(self):
		super().__init__()


	@route('/restart/')
	@ApiAuthenticated
	def restart(self):
		try:
			self.ThreadManager.doLater(interval=2, func=self.ProjectAlice.doRestart)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed restarting Alice: {e}')
			return jsonify(success=False)


	@route('/reboot/')
	@ApiAuthenticated
	def reboot(self):
		try:
			self.ThreadManager.doLater(interval=2, func=self.Commons.runRootSystemCommand, args=[['shutdown', '-r', 'now']])
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed rebooting device: {e}')
			return jsonify(success=False)
