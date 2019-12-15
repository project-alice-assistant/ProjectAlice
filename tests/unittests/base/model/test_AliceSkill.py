import unittest
from unittest import mock
from unittest.mock import MagicMock, PropertyMock

from core.base.model.AliceSkill import AliceSkill
from core.util.Decorators import IntentHandler, MqttHandler
from core.base.model.Intent import Intent
from core.user.model.AccessLevels import AccessLevel

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
			#ignore all stuff that would happen in the AliceSkill init
			def __init__(self):
				pass

			@IntentHandler('intent1', authOnly=AccessLevel.ADMIN)
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
		property_mock.protectIntent.assert_called_once()

		intent1 = mappings[str(Intent('intent1'))]
		intent2 = mappings[str(Intent('intent2'))]
		intent3 = mappings[str(Intent('intent3'))]

		self.assertFalse(intent1.protected)
		self.assertEqual(intent1.authOnly, AccessLevel.ADMIN)
		self.assertEqual(intent1.fallbackFunction, ExampleSkill.single_decorator)
		self.assertEqual(intent1.dialogMapping, dict())
		self.assertEqual(str(intent1), 'hermes/intent/unittest:intent1')

		self.assertFalse(intent2.protected)
		self.assertEqual(intent2.authOnly, 0)
		self.assertEqual(intent2.fallbackFunction, None)
		self.assertDictEqual(
			intent2.dialogMapping,
			{'exampleState': ExampleSkill.multiple_decorator,
			 'exampleState2': ExampleSkill.mqtt_decorator})
		self.assertEqual(str(intent2), 'hermes/intent/unittest:intent2')

		self.assertTrue(intent3.protected)
		self.assertEqual(intent3.authOnly, 0)
		self.assertEqual(intent3.fallbackFunction, ExampleSkill.multiple_decorator)
		self.assertEqual(intent3.dialogMapping, dict())
		self.assertEqual(str(intent3), 'hermes/intent/unittest:intent3')



if __name__ == "__main__":
	unittest.main()
