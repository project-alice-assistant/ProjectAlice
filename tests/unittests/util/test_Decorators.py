import unittest
from unittest import mock
from unittest.mock import MagicMock

from core.util.Decorators import IntentHandler, Decorators
from core.base.model.Intent import Intent

class TestDecorators(unittest.TestCase):

	def test_deprecated(self):
		@Decorators.deprecated
		def legacy_function():
			pass

		self.assertWarnsRegex(DeprecationWarning,
			f'Call to deprecated function {legacy_function.__name__}.',
			legacy_function)
	
	
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