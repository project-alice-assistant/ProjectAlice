from __future__ import annotations

from typing import Callable, Tuple, Union

import functools
import warnings

from core.base.SuperManager import SuperManager
from core.base.model.Intent import Intent
from core.util.model.Logger import Logger


def deprecated(func):
	"""
	https://stackoverflow.com/questions/2536307/decorators-in-the-python-standard-lib-deprecated-specifically
	This is a decorator which can be used to mark functions
	as deprecated. It will result in a warning being emitted
	when the function is used.
	"""

	@functools.wraps(func)
	def new_func(*args, **kwargs):
		warnings.simplefilter('always', DeprecationWarning)  # turn off filter
		warnings.warn(f'Call to deprecated function {func.__name__}.',
			category=DeprecationWarning,
			stacklevel=2)
		warnings.simplefilter('default', DeprecationWarning)  # reset filter
		return func(*args, **kwargs)

	return new_func


class IntentHandler:
	"""
	(return a) decorator to mark a function as an intent.

	This decorator can be used to map a function to a intent.

	:param requiredState:
	:param isProtected:
	:param userIntent:
	:return: return value of the decorated function
	Examples:
		An intent handler can be mapped to the intent 'intentName' the following way:

		@Intent('intentName')
		def exampleIntent(self, session: DialogSession, **_kwargs):
			request = requests.get('http://api.open-notify.org')
			self.endDialog(sessionId=session.sessionId, text=request.text)

		When the function should only be called when the current dialogState is 'currentState':

		@Intent('intentName', requiredState='currentState')
		def exampleIntent(self, session: DialogSession, **_kwargs):
			request = requests.get('http://api.open-notify.org')
			self.endDialog(sessionId=session.sessionId, text=request.text)

		In the same way all other parameters supported by the Intent class can be used in the decorator.


		Mapping multiple intents to the same function is possible aswell using
		(make sure that the intent decorators are used in front of any other decorators):

		@Intent('intentName1')
		@Intent('intentName2')
		def exampleIntent(self, session: DialogSession, **_kwargs):
			request = requests.get('http://api.open-notify.org')
			self.endDialog(sessionId=session.sessionId, text=request.text)
	"""
	class Wrapper:
		def __init__(self, method: Callable, intent: Union[str, Intent], requiredState: str, isProtected: bool, userIntent: bool):
			self.decoratedMethod = method
			self.requiredState = requiredState
			self._intent = intent
			self._isProtected = isProtected
			self._userIntent = userIntent
			self._owner = None
			functools.update_wrapper(self, method, updated=[])

		@property
		def intent(self) -> Intent:
			if isinstance(self._intent, str):
				return Intent(self._intent, isProtected=self._isProtected, userIntent=self._userIntent)
			return self._intent

		@property
		def intentName(self) -> str:
			return str(self._intent)

		def __call__(self, *args, **kwargs):
			if self._owner:
				return self.decoratedMethod(SuperManager.getInstance().skillManager.getModuleInstance(self._owner.__name__), *args, **kwargs)
			return self.decoratedMethod(*args, **kwargs)

		def __set_name__(self, owner, name):
			self._owner = owner

	def __init__(self, intent: Union[str, Intent], requiredState: str = None, isProtected: bool = False, userIntent: bool = True):
		self._intent = intent
		self._requiredState = requiredState
		self._isProtected = isProtected
		self._userIntent = userIntent

	def __call__(self, func: Callable) -> IntentHandler.Wrapper:
		return self.Wrapper(func, self._intent, self._requiredState, self._isProtected, self._userIntent)



def Online(func: Callable = None, text: str = 'offline', offlineHandler: Callable = None, returnText: bool = False):
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

	:param func:
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
		if offlineHandler:
			return offlineHandler(*args, **kwargs)

		caller = args[0] if args else None
		module = getattr(caller, 'name', 'system')
		newText = SuperManager.getInstance().talkManager.randomTalk(text, module=module)
		if not newText and module != 'system':
			newText = SuperManager.getInstance().talkManager.randomTalk(text, module='system') or text

		if returnText:
			return newText

		session = kwargs.get('session')
		try:
			if session.sessionId in SuperManager.getInstance().dialogSessionManager.sessions:
				SuperManager.getInstance().mqttManager.endDialog(sessionId=session.sessionId, text=newText)
			else:
				SuperManager.getInstance().mqttManager.say(text=newText, client=session.siteId)
		except AttributeError:
			return newText

	def argumentWrapper(func):
		@functools.wraps(func)
		def offlineDecorator(*args, **kwargs):
			internetManager = SuperManager.getInstance().internetManager
			if internetManager.online:
				try:
					return func(*args, **kwargs)
				except:
					if internetManager.checkOnlineState():
						raise

			return _offlineHandler(*args, **kwargs)

		return offlineDecorator

	return argumentWrapper(func) if func else argumentWrapper


def AnyExcept(func: Callable = None, text: str = 'error', exceptions: Tuple[BaseException, ...] = None, exceptHandler: Callable = None, returnText: bool = False, printStack: bool = False):

	def _exceptHandler(*args, **kwargs):
		if exceptHandler:
			return exceptHandler(*args, **kwargs)

		caller = args[0] if args else None
		module = getattr(caller, 'name', 'system')
		newText = SuperManager.getInstance().talkManager.randomTalk(text, module=module)
		if not newText and module != 'system':
			newText = SuperManager.getInstance().talkManager.randomTalk(text, module='system') or text

		if returnText:
			return newText

		session = kwargs.get('session')
		try:
			if session.sessionId in SuperManager.getInstance().dialogSessionManager.sessions:
				SuperManager.getInstance().mqttManager.endDialog(sessionId=session.sessionId, text=newText)
			else:
				SuperManager.getInstance().mqttManager.say(text=newText, client=session.siteId)
		except AttributeError:
			return newText

	def argumentWrapper(func):
		@functools.wraps(func)
		def exceptionDecorator(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except exceptions as e:
				Logger(depth=6).logWarning(msg=e, printStack=printStack)
				return _exceptHandler(*args, **kwargs)

		return exceptionDecorator

	exceptions = exceptions or Exception
	return argumentWrapper(func) if func else argumentWrapper
