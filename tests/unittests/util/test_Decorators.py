import unittest
from unittest import mock
from unittest.mock import MagicMock

from core.util.Decorators import IntentHandler, Decorators

class TestDecorators(unittest.TestCase):

	def test_deprecated(self):
		@Decorators.deprecated
		def legacy_function():
			pass

		self.assertWarnsRegex(DeprecationWarning,
			f'Call to deprecated function {legacy_function.__name__}.',
			legacy_function)


	@mock.patch('core.util.Decorators.SuperManager')
	def test_online(self, mock_superManager):
		class Module:
			@property
			def name(self):
				return 'Module'

			@Decorators.online
			def offline(self, *args, **kwargs):
				raise Exception

			@Decorators.online(returnText=True)
			def offline_return(self, *args, **kwargs):
				raise Exception

			def offlineHandler(self, *args, **kwargs):
				return self, args, kwargs

			@Decorators.online(offlineHandler=offlineHandler)
			def catch_offlineHandler(self, *args, **kwargs):
				raise Exception
			
			@staticmethod
			@Decorators.online
			def catch_staticMethod(*args, **kwargs):
				raise Exception

		class InternetManager:
			def __init__(self, online: bool, keepOffline: bool = False):
				self.online = online
				self.keepOffline = keepOffline

			def checkOnlineState(self):
				if not self.keepOffline:
					self.online = False



		exampleObject = Module()

		# mock Managers
		mock_instance = MagicMock()
		mock_superManager.getInstance.return_value = mock_instance
		mock_instance.talkManager.randomTalk.return_value = 'offline'
		mock_internetManager = mock.PropertyMock(return_value=InternetManager(False))
		type(mock_instance).internetManager = mock_internetManager


		# mock DialogSession
		mock_session = MagicMock()
		mock_sessionId = mock.PropertyMock(return_value='sessionId')
		type(mock_session).sessionId = mock_sessionId
		mock_siteId = mock.PropertyMock(return_value='siteId')
		type(mock_session).siteId = mock_siteId

		# when there is already no internet
		self.assertEqual(exampleObject.offline(), 'offline')
		mock_instance.talkManager.randomTalk.assert_called_once_with('offline', module='Module')
		mock_instance.reset_mock()

		# when Internet is lost
		mock_internetManager = mock.PropertyMock(return_value=InternetManager(True))
		type(mock_instance).internetManager = mock_internetManager
		
		self.assertEqual(exampleObject.offline(), 'offline')
		mock_instance.talkManager.randomTalk.assert_called_once_with('offline', module='Module')
		
		mock_internetManager = mock.PropertyMock(return_value=InternetManager(False))
		type(mock_instance).internetManager = mock_internetManager
		mock_instance.reset_mock()

		# when session is still active use endDialog
		mock_sessions = mock.PropertyMock(return_value=['sessionId'])
		type(mock_instance.dialogSessionManager).sessions = mock_sessions

		exampleObject.offline(session=mock_session)
		mock_instance.talkManager.randomTalk.assert_called_once_with('offline', module='Module')
		mock_instance.mqttManager.endDialog.assert_called_once_with(sessionId='sessionId', text='offline')
		mock_instance.reset_mock()

		# when session is finished use say
		mock_sessions = mock.PropertyMock(return_value=[])
		type(mock_instance.dialogSessionManager).sessions = mock_sessions

		exampleObject.offline(session=mock_session)
		mock_instance.talkManager.randomTalk.assert_called_once_with('offline', module='Module')
		mock_instance.mqttManager.say.assert_called_once_with(text='offline', client='siteId')
		mock_instance.reset_mock()

		# raise exception when it is not offline
		mock_internetManager = mock.PropertyMock(return_value=InternetManager(True, True))
		type(mock_instance).internetManager = mock_internetManager
		
		self.assertRaises(Exception, exampleObject.offline)
		
		mock_internetManager = mock.PropertyMock(return_value=InternetManager(False))
		type(mock_instance).internetManager = mock_internetManager
		mock_instance.reset_mock()

		# when returnText is true always return the text instead of saying it
		mock_instance.talkManager.randomTalk.return_value = None
		self.assertEqual(exampleObject.offline_return(), 'offline')
		mock_instance.talkManager.randomTalk.assert_has_calls([
			mock.call('offline', module='Module'),
			mock.call('offline', module='system')],
			any_order=True
		)
		mock_instance.talkManager.randomTalk.return_value = 'offline'
		mock_instance.reset_mock()

		# when offline handler is specified it is called correctly
		instance, args, kwargs = exampleObject.catch_offlineHandler('arg1', 'arg2', kwarg1='kwarg1', kwarg2='kwarg2')
		self.assertEqual(instance, exampleObject, "the object instance is not retrieved correctly")
		self.assertEqual(args, ('arg1', 'arg2'), "unnamed arguments are passed in a wrong way")
		self.assertEqual(kwargs, {'kwarg1': 'kwarg1', 'kwarg2': 'kwarg2'}, "named arguments are passed in a wrong way")
		mock_instance.reset_mock()

		# decorator works with staticmethod, but falls back to system
		self.assertEqual(exampleObject.catch_staticMethod(), 'offline')
		mock_instance.talkManager.randomTalk.assert_called_once_with('offline', module='system')


	@mock.patch('core.util.Decorators.Logger')
	@mock.patch('core.util.Decorators.SuperManager')
	def test_anyExcept(self, mock_superManager, mock_logger):
		class Module:
			@property
			def name(self):
				return 'Module'

			@Decorators.anyExcept
			def catch_all(self, *args, **kwargs):
				raise Exception

			@Decorators.anyExcept(exceptions=KeyError)
			def catch_ValueError(self, *args, **kwargs):
				raise Exception

			@Decorators.anyExcept(returnText=True)
			def catch_returnText(self, *args, **kwargs):
				raise Exception

			def exceptHandler(self, *args, **kwargs):
				return self, args, kwargs

			@Decorators.anyExcept(exceptHandler=exceptHandler)
			def catch_exceptionHandler(self, *args, **kwargs):
				raise Exception
			
			@staticmethod
			@Decorators.anyExcept
			def catch_staticMethod(*args, **kwargs):
				raise Exception

		exampleObject = Module()

		# mock Managers
		mock_instance = MagicMock()
		mock_superManager.getInstance.return_value = mock_instance
		mock_instance.talkManager.randomTalk.return_value = 'error'

		# mock DialogSession
		mock_session = MagicMock()
		mock_sessionId = mock.PropertyMock(return_value='sessionId')
		type(mock_session).sessionId = mock_sessionId
		mock_siteId = mock.PropertyMock(return_value='siteId')
		type(mock_session).siteId = mock_siteId

		# when no DialogSession is provided return text
		self.assertEqual(exampleObject.catch_all(), 'error')
		mock_instance.talkManager.randomTalk.assert_called_once_with('error', module='Module')
		mock_instance.reset_mock()

		# when session is still active use endDialog
		mock_sessions = mock.PropertyMock(return_value=['sessionId'])
		type(mock_instance.dialogSessionManager).sessions = mock_sessions

		exampleObject.catch_all(session=mock_session)
		mock_instance.talkManager.randomTalk.assert_called_once_with('error', module='Module')
		mock_instance.mqttManager.endDialog.assert_called_once_with(sessionId='sessionId', text='error')
		mock_instance.reset_mock()

		# when session is finished use say
		mock_sessions = mock.PropertyMock(return_value=[])
		type(mock_instance.dialogSessionManager).sessions = mock_sessions

		exampleObject.catch_all(session=mock_session)
		mock_instance.talkManager.randomTalk.assert_called_once_with('error', module='Module')
		mock_instance.mqttManager.say.assert_called_once_with(text='error', client='siteId')
		mock_instance.reset_mock()

		# raise exception when it is not in the exceptions list
		self.assertRaises(Exception, exampleObject.catch_ValueError)
		mock_instance.reset_mock()

		# when returnText is true always return the text instead of saying it
		mock_instance.talkManager.randomTalk.return_value = None
		self.assertEqual(exampleObject.catch_returnText(), 'error')
		mock_instance.talkManager.randomTalk.assert_has_calls([
			mock.call('error', module='Module'),
			mock.call('error', module='system')],
			any_order=True
		)
		mock_instance.talkManager.randomTalk.return_value = 'error'
		mock_instance.reset_mock()

		# when except handler is specified it is called correctly
		instance, args, kwargs = exampleObject.catch_exceptionHandler('arg1', 'arg2', kwarg1='kwarg1', kwarg2='kwarg2')
		self.assertEqual(instance, exampleObject, "the object instance is not retrieved correctly")
		self.assertEqual(args, ('arg1', 'arg2'), "unnamed arguments are passed in a wrong way")
		self.assertEqual(kwargs, {'kwarg1': 'kwarg1', 'kwarg2': 'kwarg2'}, "named arguments are passed in a wrong way")
		mock_instance.reset_mock()

		# decorator works with staticmethod, but falls back to system
		self.assertEqual(exampleObject.catch_staticMethod(), 'error')
		mock_instance.talkManager.randomTalk.assert_called_once_with('error', module='system')



	@mock.patch('core.util.Decorators.Intent')
	@mock.patch('core.util.Decorators.SuperManager')
	def test_IntentHandler(self, mock_superManager, mock_intent):
		class Example:
			@IntentHandler('intent1')
			def single_decorator(self, *args, **kwargs):
				return self, args, kwargs

			@IntentHandler(mock_intent('intent2'))
			@IntentHandler('intent3', isProtected=True, userIntent=False)
			def multiple_decorator(self, *args, **kwargs):
				return self, args, kwargs

		exampleObject = Example()
		mock_instance = MagicMock()
		mock_superManager.getInstance.return_value = mock_instance
		mock_instance.moduleManager.getModuleInstance.return_value = exampleObject


		# test whether the decorator works when a single intent is mapped
		instance, args, kwargs = exampleObject.single_decorator('arg1', 'arg2', kwarg1='kwarg1', kwarg2='kwarg2')
		self.assertEqual(instance, exampleObject, "the object instance is not retrieved correctly")
		self.assertEqual(args, ('arg1', 'arg2'), "unnamed arguments are passed in a wrong way")
		self.assertEqual(kwargs, {'kwarg1': 'kwarg1', 'kwarg2': 'kwarg2'}, "named arguments are passed in a wrong way")
		mock_instance.moduleManager.getModuleInstance.assert_called_once_with(Example.__name__)
		mock_instance.reset_mock()


		# test whether the decorator works when multiple intents are mapped
		instance, args, kwargs = exampleObject.multiple_decorator('arg1', 'arg2', kwarg1='kwarg1', kwarg2='kwarg2')
		self.assertEqual(instance, exampleObject, "the object instance is not retrieved correctly")
		self.assertEqual(args, ('arg1', 'arg2'), "unnamed arguments are passed in a wrong way")
		self.assertEqual(kwargs, {'kwarg1': 'kwarg1', 'kwarg2': 'kwarg2'}, "named arguments are passed in a wrong way")
		mock_instance.moduleManager.getModuleInstance.assert_called_once_with(Example.__name__)


		# test whether the intents are created correctly
		for name in dir(Example):
			method = getattr(Example, name)
			while isinstance(method, IntentHandler.Wrapper):
				method.intent
				method = method.decoratedMethod

		mock_intent.assert_has_calls([
			mock.call('intent1', isProtected=False, userIntent=True),
			mock.call('intent2'),
			mock.call('intent3', isProtected=True, userIntent=False)],
			any_order=True
		)


		#test whether the intent <-> function mapping can be retrieved correctly
		mappings = list()
		for name in dir(Example):
			originalMethod= getattr(Example, name)
			method = originalMethod
			while isinstance(method, IntentHandler.Wrapper):
				mappings.append((method.intentName, originalMethod))
				method = method.decoratedMethod

		self.assertCountEqual([
			('intent1', Example.single_decorator),
			(str(mock_intent()), Example.multiple_decorator),
			('intent3', Example.multiple_decorator)],
			mappings,
			"The intent <-> function mappings can not be retrieved correctly"
		)


if __name__ == "__main__":
	unittest.main()
