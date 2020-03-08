import unittest
from unittest import mock
from unittest.mock import MagicMock, PropertyMock

from core.base.model.AliceSkill import AliceSkill
from core.base.model.Intent import Intent
from core.user.model.AccessLevels import AccessLevel
from core.util.Decorators import IntentHandler, MqttHandler


class TestAliceSkill(unittest.TestCase):

	@mock.patch('core.util.Decorators.Intent.ProtectedIntentManager', new_callable=PropertyMock)
	@mock.patch('core.util.Decorators.Intent.ConfigManager', new_callable=PropertyMock)
	def testFindDecoratedIntents(self, mock_config, mock_protected):
		owner_mock = MagicMock()
		owner_mock.getAliceConfigByName.return_value = 'unittest'
		mock_config.return_value = owner_mock

		property_mock = MagicMock()
		mock_protected.return_value = property_mock

		class ExampleSkill(AliceSkill):

			# ignore all stuff that would happen in the AliceSkill init
			def __init__(self):
				self._name = 'ExampleSkill'


			@IntentHandler('intent1', authLevel=AccessLevel.ADMIN)
			def single_decorator(self, *args, **kwargs):
				return self, args, kwargs


			@IntentHandler('intent2', requiredState='exampleState')
			@IntentHandler('intent3', isProtected=True)
			def multiple_decorator(self, *args, **kwargs):
				return self, args, kwargs


			@MqttHandler('hermes/intent/unittest:intent2', requiredState='exampleState2')
			def mqtt_decorator(self, *args, **kwargs):
				return self, args, kwargs

		exampleSkill = ExampleSkill()

		mappings = exampleSkill.findDecoratedIntents()
		self.assertEqual(property_mock.protectIntent.call_count, 2)

		intent1 = mappings[str(Intent('intent1'))]
		intent2 = mappings[str(Intent('intent2'))]
		intent3 = mappings[str(Intent('intent3'))]

		self.assertFalse(intent1.protected)
		self.assertEqual(intent1.authOnly, AccessLevel.ADMIN)
		self.assertEqual(intent1.fallbackFunction, exampleSkill.single_decorator)
		self.assertEqual(intent1.dialogMapping, dict())
		self.assertEqual(str(intent1), 'hermes/intent/unittest:intent1')

		self.assertFalse(intent2.protected)
		self.assertEqual(intent2.authOnly, 0)
		self.assertEqual(intent2.fallbackFunction, None)
		self.assertDictEqual(
			intent2.dialogMapping,
			{'ExampleSkill:exampleState': exampleSkill.multiple_decorator,
			 'ExampleSkill:exampleState2': exampleSkill.mqtt_decorator})
		self.assertEqual(str(intent2), 'hermes/intent/unittest:intent2')

		self.assertTrue(intent3.protected)
		self.assertEqual(intent3.authOnly, 0)
		self.assertEqual(intent3.fallbackFunction, exampleSkill.multiple_decorator)
		self.assertEqual(intent3.dialogMapping, dict())
		self.assertEqual(str(intent3), 'hermes/intent/unittest:intent3')


	@mock.patch('core.util.Decorators.Intent.ProtectedIntentManager', new_callable=PropertyMock)
	@mock.patch('core.util.Decorators.Intent.ConfigManager', new_callable=PropertyMock)
	@mock.patch('core.base.model.AliceSkill.AliceSkill.findDecoratedIntents')
	def testBuildIntentList(self, mock_decoratedFuncs, mock_config, mock_protected):
		owner_mock = MagicMock()
		owner_mock.getAliceConfigByName.return_value = 'unittest'
		mock_config.return_value = owner_mock

		property_mock = MagicMock()
		mock_protected.return_value = property_mock

		class ExampleSkill(AliceSkill):
			#ignore all stuff that would happen in the AliceSkill init
			def __init__(self):
				self._name = 'ExampleSkill'

			def exampleFunc(self):
				pass

		exampleSkill = ExampleSkill()


		# no decorated functions no initialised values
		mock_decoratedFuncs.return_value = {}
		self.assertDictEqual(
			exampleSkill.buildIntentList(list()),
			dict()
		)

		# no decorated functions
		initIntents = [
			Intent('Intent1', authLevel=AccessLevel.ADMIN),
			'hermes/intent/unittest:Intent2',
			(Intent('intent3'), exampleSkill.exampleFunc),
			('hermes/intent/unittest:intent4', exampleSkill.exampleFunc)
		]

		mappings = exampleSkill.buildIntentList(initIntents)
		intent1 = mappings[str(Intent('Intent1'))]
		intent2 = mappings[str(Intent('Intent2'))]
		intent3 = mappings[str(Intent('intent3'))]
		intent4 = mappings[str(Intent('intent4'))]

		self.assertFalse(intent1.protected)
		self.assertEqual(intent1.authOnly, AccessLevel.ADMIN)
		self.assertEqual(intent1.fallbackFunction, None)
		self.assertEqual(intent1.dialogMapping, dict())
		self.assertEqual(str(intent1), 'hermes/intent/unittest:Intent1')

		self.assertFalse(intent2.protected)
		self.assertEqual(intent2.authOnly, 0)
		self.assertEqual(intent2.fallbackFunction, None)
		self.assertEqual(intent2.dialogMapping, dict())
		self.assertEqual(str(intent2), 'hermes/intent/unittest:Intent2')

		self.assertFalse(intent3.protected)
		self.assertEqual(intent3.authOnly, 0)
		self.assertEqual(intent3.fallbackFunction, exampleSkill.exampleFunc)
		self.assertEqual(intent3.dialogMapping, dict())
		self.assertEqual(str(intent3), 'hermes/intent/unittest:intent3')

		self.assertFalse(intent4.protected)
		self.assertEqual(intent4.authOnly, 0)
		self.assertEqual(intent4.fallbackFunction, exampleSkill.exampleFunc)
		self.assertEqual(intent4.dialogMapping, dict())
		self.assertEqual(str(intent4), 'hermes/intent/unittest:intent4')


		# decorated functions
		intent1 = Intent('intent1')
		intent1.fallbackFunction = exampleSkill.onMessage
		mock_decoratedFuncs.return_value = {
			'hermes/intent/unittest:intent1': intent1,
		}

		initIntents = [
			Intent('intent1', authLevel=AccessLevel.ADMIN)
		]

		mappings = exampleSkill.buildIntentList(initIntents)
		intent1 = mappings[str(Intent('intent1'))]

		self.assertFalse(intent1.protected)
		self.assertEqual(intent1.authOnly, AccessLevel.ADMIN)
		self.assertEqual(intent1.fallbackFunction, exampleSkill.onMessage)
		self.assertEqual(intent1.dialogMapping, dict())
		self.assertEqual(str(intent1), 'hermes/intent/unittest:intent1')


if __name__ == "__main__":
	unittest.main()
