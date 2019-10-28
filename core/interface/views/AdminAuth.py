from flask import render_template, request, jsonify, redirect
from flask_login import login_user, current_user

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

		if current_user.is_authenticated:
			return render_template(self.__class__.nextPage, langData=self._langData)

		self.ModuleManager.getModuleInstance('AliceCore').explainInterfaceAuth()
		return render_template('adminAuth.html', langData=self._langData)


	def checkAuthState(self):
		if current_user.is_authenticated:
			return jsonify(success=True)
		else:
			return jsonify(success=False)



	def authenticate(self):
		try:
			code = request.form.get('usercode')
			if self.UserManager.checkPinCode(self.__class__.user, str(code)):
				return jsonify(success=True)
			else:
				return jsonify(success=False)
		except Exception as e:
			self.logError(f'Failed auth trial: {e}')
			return jsonify(success=False)


	@classmethod
	def loginUser(cls):
		login_user(cls.user)


	@classmethod
	def setNextPage(cls, url: str):
		cls.nextPage = url


	@classmethod
	def getNextPage(cls) -> str:
		return cls.nextPage
