import datetime

from flask import jsonify, redirect, render_template, request
from flask_login import current_user, login_user

from core.dialog.model.DialogSession import DialogSession
from core.interface.model.View import View
from core.user.model.User import User


class AdminAuth(View):
	route_base = '/adminAuth/'

	nextPage = 'index'
	user = None
	linkedSnipsSession = None


	def index(self):
		try:
			self.__class__.setNextPage(request.args.get('next'))
		except:
			self.logWarning('No next page after auth success, falling back to index.html')

		if current_user.is_authenticated:
			return redirect(self.__class__.nextPage)

		self.SkillManager.getSkillInstance('AliceCore').explainInterfaceAuth()
		return render_template(template_name_or_list='adminAuth.html',
		                       langData=self._langData,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)


	def checkAuthState(self):
		if self.__class__.user is not None:
			if self.__class__.user.isAuthenticated:
				login_user(user=self.__class__.user, duration=datetime.timedelta(minutes=15))
				return jsonify(nextPage=self.__class__.nextPage)
			else:
				return jsonify(username=self.__class__.user.name)
		else:
			return jsonify(success=False)


	def login(self):
		try:
			username = request.form.get('username', None)
			if not username:
				return jsonify(success=False)

			user = self.UserManager.getUser(username)
			if not user:
				return jsonify(success=False)

			self.setUser(user)

			return jsonify(success=True)
		except:
			self.logError('Failed login via keyboard')
			return jsonify(success=False)


	def authenticate(self):
		try:
			code = request.form.get('usercode')
			if self.UserManager.checkPinCode(self.__class__.user, str(code)):
				self.__class__.user.isAuthenticated = True
				return jsonify(success=True)

		except Exception as e:
			self.logError(f'Failed auth trial: {e}')

		return jsonify(success=False)


	def keyboardAuth(self):
		self.SkillManager.getSkillInstance('AliceCore').authWithKeyboard()
		if self.__class__.linkedSnipsSession is not None:
			self.MqttManager.endSession(sessionId=self.__class__.linkedSnipsSession.sessionId)
		return jsonify(success=True)


	@classmethod
	def setNextPage(cls, url: str):
		cls.nextPage = url


	@classmethod
	def getNextPage(cls) -> str:
		return cls.nextPage


	@classmethod
	def setUser(cls, user: User = None):
		cls.user = user


	@classmethod
	def getUser(cls) -> User:
		return cls.user


	@classmethod
	def setLinkedSnipsSession(cls, session: DialogSession):
		cls.linkedSnipsSession = session
