from typing import Callable

import warnings

import functools

from core.base.model.Module import Module
from core.dialog.model.DialogSession import DialogSession


class Decorators:
	@classmethod
	def deprecated(cls, func):
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


		def argumentWrapper(func):
			def functionWrapper(*args, **kwargs):
				nonlocal text
				caller = args[0] if args and isinstance(args[0], Module) else None
				internetManager = caller.InternetManager
				if internetManager.online:
					try:
						return func(*args, **kwargs)
					except:
						internetManager.checkOnlineState()
						if internetManager.online:
							raise

				if offlineHandler:
					return offlineHandler(*args, **kwargs)
				if callable(text) or not text:
					text = caller.TalkManager.randomTalk('offline', module='system')
				elif hasattr(caller, 'name'):
					text = caller.TalkManager.randomTalk(text, module=caller.name)
				if returnText:
					return text
				session = kwargs.get('session')
				if isinstance(session, DialogSession):
					caller.MqttManager.endDialog(sessionId=session.sessionId, text=text)

			return functionWrapper

		if callable(text):
			return argumentWrapper(text)
		return argumentWrapper
