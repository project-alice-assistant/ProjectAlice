from flask import render_template, request, jsonify, redirect

from core.interface.model.View import View


class AdminAuth(View):
	route_base = '/adminAuth/'

	nextPage = 'index'
	user = None


	def index(self):
		try:
			self.__class__.setNextPage(request.args.get('next'))
		except:
			self.logWarning('No next page after auth success, falling back to index.html')

		if self.__class__.user and self.__class__.user.isAuthenticated:
			return redirect(self.__class__.nextPage)
		else:
			self.ModuleManager.getModuleInstance('AliceCore').explainInterfaceAuth()
			return render_template('adminAuth.html', langData=self._langData)


	def checkAuthState(self):
		return jsonify(success=True if self.__class__.user and self.__class__.user.isAuthenticated else False)


	def authenticate(self):
		try:
			code = request.form.get('usercode')
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed auth trial: {e}')
			return jsonify(success=False)


	@classmethod
	def setNextPage(cls, url: str):
		cls.nextPage = url


	@classmethod
	def getNextPage(cls) -> str:
		return cls.nextPage
