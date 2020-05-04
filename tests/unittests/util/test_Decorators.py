import unittest
from unittest import mock
from unittest.mock import MagicMock

from core.util.Decorators import AnyExcept, IntentHandler, Online, deprecated


class TestDecorators(unittest.TestCase):

	def test_deprecated(self):
		@deprecated
		def legacy_function():
			pass

		self.assertWarnsRegex(DeprecationWarning,
			f'Call to deprecated function {legacy_function.__name__}.',
			legacy_function)


	@mock.patch('core.util.Decorators.SuperManager')
	def test_online(self, mock_superManager):
		class AliceSkill:
			@property
			def name(self):
				return 'AliceSkill'

			@Online
			def offline(self, *args, **kwargs):
				raise Exception

			@Online(returnText=True)
			def offline_return(self, *args, **kwargs):
				raise Exception

			def offlineHandler(self, *args, **kwargs):
				return self, args, kwargs

			@Online(offlineHandler=offlineHandler)
			def catch_offlineHandler(self, *args, **kwargs):
				raise Exception

			@staticmethod
			@Online
			def catch_staticMethod(*args, **kwargs):
				raise Exception

		class InternetManager:
			def __init__(self, online: bool, keepOffline: bool = False):
				self.online = online
				self.keepOffline = keepOffline

			def checkOnlineState(self) -> bool:
				if not self.keepOffline:
					self.online = False
				return self.online



		exampleObject = AliceSkill()

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
		mock_instance.talkManager.randomTalk.assert_called_once_with('offline', skill='AliceSkill')
		mock_instance.reset_mock()

		# when Internet is lost
		mock_internetManager = mock.PropertyMock(return_value=InternetManager(True))
		type(mock_instance).internetManager = mock_internetManager

		self.assertEqual(exampleObject.offline(), 'offline')
		mock_instance.talkManager.randomTalk.assert_called_once_with('offline', skill='AliceSkill')

		mock_internetManager = mock.PropertyMock(return_value=InternetManager(False))
		type(mock_instance).internetManager = mock_internetManager
		mock_instance.reset_mock()

		# when session is still active use endDialog
		mock_sessions = mock.PropertyMock(return_value=['sessionId'])
		type(mock_instance.dialogManager).sessions = mock_sessions

		exampleObject.offline(session=mock_session)
		mock_instance.talkManager.randomTalk.assert_called_once_with('offline', skill='AliceSkill')
		mock_instance.mqttManager.endDialog.assert_called_once_with(sessionId='sessionId', text='offline')
		mock_instance.reset_mock()

		# when session is finished use say
		mock_sessions = mock.PropertyMock(return_value=[])
		type(mock_instance.dialogManager).sessions = mock_sessions

		exampleObject.offline(session=mock_session)
		mock_instance.talkManager.randomTalk.assert_called_once_with('offline', skill='AliceSkill')
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
			mock.call('offline', skill='AliceSkill'),
			mock.call('offline', skill='system')],
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
		mock_instance.talkManager.randomTalk.assert_called_once_with('offline', skill='system')


	@mock.patch('core.util.Decorators.Logger')
	@mock.patch('core.util.Decorators.SuperManager')
	def test_anyExcept(self, mock_superManager, mock_logger):
		class AliceSkill:
			@property
			def name(self):
				return 'AliceSkill'

			@AnyExcept
			def catch_all(self, *args, **kwargs):
				raise Exception

			@AnyExcept(exceptions=KeyError)
			def catch_ValueError(self, *args, **kwargs):
				raise Exception

			@AnyExcept(returnText=True)
			def catch_returnText(self, *args, **kwargs):
				raise Exception

			def exceptHandler(self, *args, **kwargs):
				return self, args, kwargs

			@AnyExcept(exceptHandler=exceptHandler)
			def catch_exceptionHandler(self, *args, **kwargs):
				raise Exception

			@staticmethod
			@AnyExcept
			def catch_staticMethod(*args, **kwargs):
				raise Exception

		exampleObject = AliceSkill()

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
		mock_instance.talkManager.randomTalk.assert_called_once_with('error', skill='AliceSkill')
		mock_instance.reset_mock()

		# when session is still active use endDialog
		mock_sessions = mock.PropertyMock(return_value=['sessionId'])
		type(mock_instance.dialogManager).sessions = mock_sessions

		exampleObject.catch_all(session=mock_session)
		mock_instance.talkManager.randomTalk.assert_called_once_with('error', skill='AliceSkill')
		mock_instance.mqttManager.endDialog.assert_called_once_with(sessionId='sessionId', text='error')
		mock_instance.reset_mock()

		# when session is finished use say
		mock_sessions = mock.PropertyMock(return_value=[])
		type(mock_instance.dialogManager).sessions = mock_sessions

		exampleObject.catch_all(session=mock_session)
		mock_instance.talkManager.randomTalk.assert_called_once_with('error', skill='AliceSkill')
		mock_instance.mqttManager.say.assert_called_once_with(text='error', client='siteId')
		mock_instance.reset_mock()

		# raise exception when it is not in the exceptions list
		self.assertRaises(Exception, exampleObject.catch_ValueError)
		mock_instance.reset_mock()

		# when returnText is true always return the text instead of saying it
		mock_instance.talkManager.randomTalk.return_value = None
		self.assertEqual(exampleObject.catch_returnText(), 'error')
		mock_instance.talkManager.randomTalk.assert_has_calls([
			mock.call('error', skill='AliceSkill'),
			mock.call('error', skill='system')],
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
		mock_instance.talkManager.randomTalk.assert_called_once_with('error', skill='system')



	@mock.patch('core.util.Decorators.Intent')
	def test_IntentHandler(self, mock_intent):
		class Example:
			@IntentHandler('intent1')
			def single_decorator(self, *args, **kwargs):
				return self, args, kwargs

			@IntentHandler(mock_intent('intent2'))
			@IntentHandler('intent3', isProtected=True)
			def multiple_decorator(self, *args, **kwargs):
				return self, args, kwargs

		exampleObject = Example()

		# test whether the decorator works when a single intent is mapped
		instance, args, kwargs = exampleObject.single_decorator('arg1', 'arg2', kwarg1='kwarg1', kwarg2='kwarg2')
		self.assertEqual(instance, exampleObject, "the object instance is not retrieved correctly")
		self.assertEqual(args, ('arg1', 'arg2'), "unnamed arguments are passed in a wrong way")
		self.assertEqual(kwargs, {'kwarg1': 'kwarg1', 'kwarg2': 'kwarg2'}, "named arguments are passed in a wrong way")


		# test whether the decorator works when multiple intents are mapped
		instance, args, kwargs = exampleObject.multiple_decorator('arg1', 'arg2', kwarg1='kwarg1', kwarg2='kwarg2')
		self.assertEqual(instance, exampleObject, "the object instance is not retrieved correctly")
		self.assertEqual(args, ('arg1', 'arg2'), "unnamed arguments are passed in a wrong way")
		self.assertEqual(kwargs, {'kwarg1': 'kwarg1', 'kwarg2': 'kwarg2'}, "named arguments are passed in a wrong way")

		self.assertCountEqual(
			Example.single_decorator.intents,
			[{'intent': mock_intent(), 'requiredState': None}],
			"The intent <-> function mappings can not be retrieved correctly"
		)

		self.assertCountEqual(
			Example.multiple_decorator.intents,
			[{'intent': mock_intent(), 'requiredState': None},
			 {'intent': mock_intent(), 'requiredState': None}],
			"The intent <-> function mappings can not be retrieved correctly"
		)


if __name__ == "__main__":
	unittest.main()
