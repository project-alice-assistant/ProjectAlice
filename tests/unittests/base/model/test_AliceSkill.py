import unittest
from unittest import mock
from unittest.mock import MagicMock

from core.base.model.AliceSkill import AliceSkill
from core.util.Decorators import IntentHandler

class TestAliceSkill(unittest.TestCase):
	@mock.patch('core.util.Decorators.Intent')
	@mock.patch('core.util.Decorators.SuperManager')
	def testDecoratedIntentMethods(self, mock_superManager, mock_intent):
		class ExampleSkill(AliceSkill):
			#ignore all stuff that would happen in the AliceSkill init
			def __init__(self):
				pass

			@IntentHandler('intent1')
			def single_decorator(self, *args, **kwargs):
				return self, args, kwargs

			@IntentHandler('intent2', requiredState='exampleState')
			@IntentHandler('intent3', isProtected=True)
			def multiple_decorator(self, *args, **kwargs):
				return self, args, kwargs
		
		exampleSkill = ExampleSkill()
		mock_instance = MagicMock()
		mock_superManager.getInstance.return_value = mock_instance
		mock_instance.skillManager.getSkillInstance.return_value = exampleSkill

		mappings = exampleSkill.intentMethods()
		mock_intent.assert_any_call('intent1', isProtected=False, userIntent=True)
		mock_intent.assert_any_call('intent3', isProtected=True, userIntent=True)
		mock_intent.assert_any_call('intent2', isProtected=False, userIntent=True)
		mock_intent.return_value.addDialogMapping.assert_called_once_with({'exampleState': exampleSkill.multiple_decorator})
		
		self.assertCountEqual([
			mock_intent(),
			(mock_intent(), exampleSkill.single_decorator),
			(mock_intent(), exampleSkill.multiple_decorator)],
			mappings,
			"The intent <-> function mappings can not be retrieved correctly"
		)



if __name__ == "__main__":
	unittest.main()
