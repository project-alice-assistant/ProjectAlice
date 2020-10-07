import unittest
from unittest import mock
from unittest.mock import MagicMock, PropertyMock

from core.base.model.AliceSkill import AliceSkill
from core.base.model.Intent import Intent
from core.base.model.Version import Version
from core.user.model.AccessLevels import AccessLevel
from core.util.Decorators import IntentHandler, MqttHandler


class TestAliceSkill(unittest.TestCase):

	@mock.patch('core.base.ConfigManager.ConfigManager', new_callable=PropertyMock)
	def testFindDecoratedIntents(self, mock_config):
		owner_mock = MagicMock()
		owner_mock.getAliceConfigByName.return_value = 'unittest'
		mock_config.return_value = owner_mock


		class ExampleSkill(AliceSkill):

			# ignore all stuff that would happen in the AliceSkill init
			# noinspection PyMissingConstructor
			def __init__(self):
				self._name = 'ExampleSkill'
				self._instructions = ''
				self._author = 'unittest'
				self._version = '0.0.1'
				self._icon = ''
				self._description = ''
				self._category = 'undefined'
				self._conditions = dict()
				self._updateAvailable = False
				self._active = False
				self._delayed = False
				self._required = False
				self._databaseSchema = dict()
				self._widgets = dict()
				self._deviceTypes = dict()
				self._intentsDefinitions = dict()
				self._scenarioNodeName = ''
				self._scenarioNodeVersion = Version(mainVersion=0, updateVersion=0, hotfix=0)


			@IntentHandler('intent1', authLevel=AccessLevel.ADMIN)
			def single_decorator(self, *args, **kwargs):
				return self, args, kwargs


			@IntentHandler('intent2', requiredState='exampleState')
			@IntentHandler('intent3')
			@IntentHandler('intent4', userIntent=False)
			def multiple_decorator(self, *args, **kwargs):
				return self, args, kwargs


			@MqttHandler('hermes/intent/intent2', requiredState='exampleState2')
			def mqtt_decorator(self, *args, **kwargs):
				return self, args, kwargs


		exampleSkill = ExampleSkill()

		mappings = exampleSkill.findDecoratedIntents()

		intent1 = mappings[str(Intent('intent1'))]
		intent2 = mappings[str(Intent('intent2'))]
		intent3 = mappings[str(Intent('intent3'))]
		intent4 = mappings[str(Intent('intent4', userIntent=False))]

		self.assertEqual(intent1.authLevel, AccessLevel.ADMIN)
		self.assertEqual(intent1.fallbackFunction, exampleSkill.single_decorator)
		self.assertEqual(intent1.dialogMapping, dict())
		self.assertEqual(str(intent1), 'hermes/intent/intent1')

		self.assertEqual(intent2.authLevel, 0)
		self.assertEqual(intent2.fallbackFunction, None)
		self.assertDictEqual(
			intent2.dialogMapping,
			{
				'ExampleSkill:exampleState' : exampleSkill.multiple_decorator,
				'ExampleSkill:exampleState2': exampleSkill.mqtt_decorator
			}
		)
		self.assertEqual(str(intent2), 'hermes/intent/intent2')

		self.assertEqual(intent3.authLevel, 0)
		self.assertEqual(intent3.fallbackFunction, exampleSkill.multiple_decorator)
		self.assertEqual(intent3.dialogMapping, dict())
		self.assertEqual(str(intent3), 'hermes/intent/intent3')
		self.assertEqual(str(intent4), 'intent4')


	@mock.patch('core.base.ConfigManager.ConfigManager', new_callable=PropertyMock)
	@mock.patch('core.base.model.AliceSkill.AliceSkill.findDecoratedIntents')
	def testBuildIntentList(self, mock_decoratedFuncs, mock_config):
		owner_mock = MagicMock()
		owner_mock.getAliceConfigByName.return_value = 'unittest'
		mock_config.return_value = owner_mock

		class ExampleSkill(AliceSkill):
			#ignore all stuff that would happen in the AliceSkill init
			# noinspection PyMissingConstructor
			def __init__(self):
				self._name = 'ExampleSkill'
				self._instructions = ''
				self._author = 'unittest'
				self._version = '0.0.1'
				self._icon = ''
				self._description = ''
				self._category = 'undefined'
				self._conditions = dict()
				self._updateAvailable = False
				self._active = False
				self._delayed = False
				self._required = False
				self._databaseSchema = dict()
				self._widgets = dict()
				self._deviceTypes = dict()
				self._intentsDefinitions = dict()
				self._scenarioNodeName = ''
				self._scenarioNodeVersion = Version(mainVersion=0, updateVersion=0, hotfix=0)

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
			'hermes/intent/Intent2',
			(Intent('intent3'), exampleSkill.exampleFunc),
			('hermes/intent/intent4', exampleSkill.exampleFunc)
		]

		mappings = exampleSkill.buildIntentList(initIntents)
		intent1 = mappings[str(Intent('Intent1'))]
		intent2 = mappings[str(Intent('Intent2'))]
		intent3 = mappings[str(Intent('intent3'))]
		intent4 = mappings[str(Intent('intent4'))]

		self.assertEqual(intent1.authLevel, AccessLevel.ADMIN)
		self.assertEqual(intent1.fallbackFunction, None)
		self.assertEqual(intent1.dialogMapping, dict())
		self.assertEqual(str(intent1), 'hermes/intent/Intent1')

		self.assertEqual(intent2.authLevel, 0)
		self.assertEqual(intent2.fallbackFunction, None)
		self.assertEqual(intent2.dialogMapping, dict())
		self.assertEqual(str(intent2), 'hermes/intent/Intent2')

		self.assertEqual(intent3.authLevel, 0)
		self.assertEqual(intent3.fallbackFunction, exampleSkill.exampleFunc)
		self.assertEqual(intent3.dialogMapping, dict())
		self.assertEqual(str(intent3), 'hermes/intent/intent3')

		self.assertEqual(intent4.authLevel, 0)
		self.assertEqual(intent4.fallbackFunction, exampleSkill.exampleFunc)
		self.assertEqual(intent4.dialogMapping, dict())
		self.assertEqual(str(intent4), 'hermes/intent/intent4')

		initIntents = [
			Intent('intent5', authLevel=AccessLevel.ADMIN)
		]
		mappings = exampleSkill.buildIntentList(initIntents)
		intent5 = mappings[str(Intent('intent5'))]

		self.assertEqual(intent5.authLevel, AccessLevel.ADMIN)
		self.assertEqual(intent5.dialogMapping, dict())
		self.assertEqual(str(intent5), 'hermes/intent/intent5')


if __name__ == '__main__':
	unittest.main()
