from __future__ import annotations

from typing import Callable, Tuple, Union

import functools
import warnings
from flask import jsonify, request

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


def IntentHandler(intent: Union[str, Intent], requiredState: str = None, isProtected: bool = False, authOnly=0):
	"""Decorator for adding a method as an intent handler."""
	if isinstance(intent, str):
		intent = Intent(intent, isProtected=isProtected, userIntent=True, authOnly=authOnly)

	def wrapper(func):
		# store the intent in the function
		if not hasattr(func, 'intents'):
			func.intents = []
		func.intents.append({'intent': intent, 'requiredState': requiredState})
		return func

	return wrapper


def MqttHandler(intent: Union[str, Intent], requiredState: str = None, isProtected: bool = True, authOnly=0):
	"""Decorator for adding a method as a mqtt handler."""
	if isinstance(intent, str):
		intent = Intent(intent, isProtected=isProtected, userIntent=False, authOnly=authOnly)

	def wrapper(func):
		# store the intent in the function
		if not hasattr(func, 'intents'):
			func.intents = []
		func.intents.append({'intent': intent, 'requiredState': requiredState})
		return func

	return wrapper


def _exceptHandler(*args, text: str, exceptHandler: Callable, returnText: bool, **kwargs):
	if exceptHandler:
		return exceptHandler(*args, **kwargs)

	caller = args[0] if args else None
	skill = getattr(caller, 'name', 'system')
	newText = SuperManager.getInstance().talkManager.randomTalk(text, skill=skill)
	if not newText and skill != 'system':
		newText = SuperManager.getInstance().talkManager.randomTalk(text, skill='system') or text

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

			return _exceptHandler(*args, text=text, exceptHandler=offlineHandler, returnText=returnText, **kwargs)

		return offlineDecorator

	return argumentWrapper(func) if func else argumentWrapper


def AnyExcept(func: Callable = None, text: str = 'error', exceptions: Tuple[BaseException, ...] = None, exceptHandler: Callable = None, returnText: bool = False, printStack: bool = False):
	def argumentWrapper(func):
		@functools.wraps(func)
		def exceptionDecorator(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except exceptions as e:
				Logger(depth=6).logWarning(msg=e, printStack=printStack)
				return _exceptHandler(*args, text=text, exceptHandler=exceptHandler, returnText=returnText, **kwargs)


		return exceptionDecorator


	exceptions = exceptions or Exception
	return argumentWrapper(func) if func else argumentWrapper


def ApiAuthenticated(func: Callable):
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		if SuperManager.getInstance().userManager.apiTokenValid(request.headers.get('auth', '')):
			return func(*args, **kwargs)
		else:
			return jsonify(message='ERROR: Unauthorized')


	return wrapper
