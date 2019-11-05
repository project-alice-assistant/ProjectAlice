from typing import Callable, Tuple

import warnings

from functools import wraps

from core.base.model.Module import Module
from core.dialog.model.DialogSession import DialogSession
from core.base.SuperManager import SuperManager
from core.util.model.Logger import Logger


class Decorators:

	@classmethod
	def deprecated(cls, func):
		"""
		https://stackoverflow.com/questions/2536307/decorators-in-the-python-standard-lib-deprecated-specifically
		This is a decorator which can be used to mark functions
		as deprecated. It will result in a warning being emitted
		when the function is used.
		"""

		@wraps(func)
		def new_func(*args, **kwargs):
			warnings.simplefilter('always', DeprecationWarning)  # turn off filter
			warnings.warn(f'Call to deprecated function {func.__name__}.',
				category=DeprecationWarning,
				stacklevel=2)
			warnings.simplefilter('default', DeprecationWarning)  # reset filter
			return func(*args, **kwargs)


		return new_func


	@classmethod
	def online(cls, text: str = '', offlineHandler: Callable = None, returnText: bool = False):
		"""
		(return a) decorator to mark a function that requires ethernet.

		This decorator can be used (with or or without parameters) to define
		a function that requires ethernet. In the Default mode without arguments shown
		in the example it will either execute whats in the function or when alice is
		offline ends the dialog with a random offline answer.
		Using the parameters:
			@online(text=<myText>)
		a own text can be used when being offline aswell and using the parameters:
			@online(offlineHandler=<myFunc>)
		a own offline handler can be called, which is helpful when not only endDialog has to be called,
		but some other cleanup is required aswell

		When there is no named argument 'session' of type DialogSession in the arguments of the decorated function,
		the decorator will return the text instead. This behaviour can be enforced aswell using:
			@online(returnText=True)

		:param text:
		:param offlineHandler:
		:param returnText:
		:return: return value of function or random offline string in the current language
		Examples:
			An intent that requires ethernet can be defined the following way:

			@online
			def exampleIntent(self, session: DialogSession, **_kwargs):
				request = requests.get('http://api.open-notify.org')
				self.endDialog(sessionId=session.sessionId, text=request.text)
		"""
		def _offlineHandler(*args, **kwargs):
			nonlocal text

			if offlineHandler:
				return offlineHandler(*args, **kwargs)

			caller = args[0] if args and isinstance(args[0], Module) else None

			if callable(text) or not text:
				text = SuperManager.getInstance().talkManager.randomTalk('offline', module='system')
			elif hasattr(caller, 'name'):
				text = SuperManager.getInstance().talkManager.randomTalk(text, module=caller.name)

			session = kwargs.get('session')
			if not returnText and isinstance(session, DialogSession):
				if session.sessionId in SuperManager.getInstance().dialogSessionManager.sessions:
					SuperManager.getInstance().mqttManager.endDialog(sessionId=session.sessionId, text=text)
				else:
					SuperManager.getInstance().mqttManager.say(text=text, client=session.siteId)
			return text

		def argumentWrapper(func):
			@wraps(func)
			def offlineDecorator(*args, **kwargs):
				internetManager = SuperManager.getInstance().internetManager
				if internetManager.online:
					try:
						return func(*args, **kwargs)
					except:
						internetManager.checkOnlineState()
						if internetManager.online:
							raise

				return _offlineHandler(*args, **kwargs)

			return offlineDecorator

		return argumentWrapper(text) if callable(text) else argumentWrapper


	@classmethod
	def anyExcept(cls, text: str = '', exceptions: Tuple[BaseException, ...] = None, exceptHandler: Callable = None, returnText: bool = False, printStack: bool = False):

		def _exceptHandler(*args, **kwargs):
			nonlocal text

			if exceptHandler:
				return exceptHandler(*args, **kwargs)

			caller = args[0] if args and isinstance(args[0], Module) else None

			if callable(text) or not text:
				text = SuperManager.getInstance().talkManager.randomTalk('error', module='system')
			elif hasattr(caller, 'name'):
				text = SuperManager.getInstance().talkManager.randomTalk(text, module=caller.name)

			session = kwargs.get('session')
			if not returnText and isinstance(session, DialogSession):
				if session.sessionId in SuperManager.getInstance().dialogSessionManager.sessions:
					SuperManager.getInstance().mqttManager.endDialog(sessionId=session.sessionId, text=text)
				else:
					SuperManager.getInstance().mqttManager.say(text=text, client=session.siteId)
			return text

		def argumentWrapper(func):
			@wraps(func)
			def exceptionDecorator(*args, **kwargs):
				try:
					return func(*args, **kwargs)
				except exceptions as e:
					Logger(depth=6).logWarning(msg=e, printStack=printStack)
					return _exceptHandler(*args, **kwargs)

			return exceptionDecorator

		exceptions = exceptions or Exception
		return argumentWrapper(text) if callable(text) else argumentWrapper


	class Intent:
		class IntentWrapper:
			def __init__(self, intentName: str, requiredState: str, isProtected: bool, userIntent: bool, method: Callable):
				self.intent = intentName
				self.requiredState = requiredState
				self.isProtected = isProtected
				self.userIntent = userIntent
				self._method = method

			def __call__(self, *args, **kwargs):
				return self._method(*args, **kwargs)

		def __init__(self, intentName: str, requiredState: str = None, isProtected: bool = False, userIntent: bool = True):
			self._intentName = intentName
			self._requiredState = requiredState
			self._isProtected = isProtected
			self._userIntent = userIntent

		def __call__(self, func: Callable):
			return self.IntentWrapper(self._intentName, func, self._requiredState, self._isProtected, self._userIntent)




