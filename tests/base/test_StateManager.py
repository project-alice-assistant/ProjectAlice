import unittest
from unittest.mock import MagicMock, patch

from core.base.StateManager import StateManager
from core.base.model.State import State
from core.base.model.StateType import StateType


class test_StateManager(unittest.TestCase):


	@patch('core.base.SuperManager.SuperManager')
	def test_register(self, mock_superManager):
		mock_instance = MagicMock()
		mock_superManager.getInstance.return_value = mock_instance
		mock_instance.commonsManager.getFunctionCaller.return_value = 'unittest'
		stateManager = StateManager()

		mockState = State('unittest')
		data = {
			'unittest': mockState
		}
		self.assertEqual(stateManager.register('unittest'), mockState)
		self.assertDictEqual(data, stateManager.states)
		self.assertIsNone(stateManager.register('unittest'))

		stateManager = StateManager()
		mockState = State('test')
		data = {
			'unit': {
				'test': mockState
			}
		}
		self.assertEqual(stateManager.register('unit.test'), mockState)
		self.assertDictEqual(data, stateManager.states)
		self.assertIsNone(stateManager.register('unit.test'))
		self.assertIsInstance(stateManager.register('unit.tests'), State)


	@patch('core.base.SuperManager.SuperManager')
	def test_get_state(self, mock_superManager):
		mock_instance = MagicMock()
		mock_superManager.getInstance.return_value = mock_instance
		mock_instance.commonsManager.getFunctionCaller.return_value = 'unittest'
		stateManager = StateManager()

		self.assertIsNone(stateManager.getState('unittest'))

		stateManager.register('unit.test.is.awesome')
		self.assertIsNone(stateManager.getState('unit.tests'))
		self.assertIsNone(stateManager.getState('unit.test.is'))
		self.assertIsInstance(stateManager.getState('unit.test.is.awesome'), State)

		stateManager.register('unit.alice.is.awesome')
		self.assertIsNone(stateManager.getState('unit.tests'))
		self.assertIsNone(stateManager.getState('unit.test.is'))
		self.assertIsInstance(stateManager.getState('unit.alice.is.awesome'), State)


	@patch('core.base.SuperManager.SuperManager')
	def test_set_state(self, mock_superManager):

		dummy = MagicMock()
		dummy.get.return_value = 'unittest'

		mock_instance = MagicMock()
		mock_superManager.getInstance.return_value = mock_instance
		mock_instance.commonsManager.getFunctionCaller.return_value = 'unittest'
		stateManager = StateManager()

		mockState = State('awesome')

		stateManager.register('unit.test.is.awesome')
		state = stateManager.getState('unit.test.is.awesome')
		self.assertEqual(state, mockState)

		stateManager.setState('unit.test.is.awesome', StateType.WAITING)
		state = stateManager.getState('unit.test.is.awesome')
		self.assertEqual(state.currentState, StateType.WAITING)

		state.subscribe(dummy.get)
		stateManager.setState('unit.test.is.awesome', StateType.STOPPED)
		dummy.get.assert_called_once_with(StateType.WAITING, StateType.STOPPED)


	@patch('core.base.SuperManager.SuperManager')
	def test_all_states(self, mock_superManager):
		mock_instance = MagicMock()
		mock_superManager.getInstance.return_value = mock_instance
		mock_instance.commonsManager.getFunctionCaller.return_value = 'unittest'
		stateManager = StateManager()

		stateManager.register('unit.test.is.awesome')
		stateManager.register('alice.also')

		states = [
			State('awesome'),
			State('also')
		]

		self.assertListEqual(stateManager.allStates(), states)


	@patch('core.base.SuperManager.SuperManager')
	def test_on_stop(self, mock_superManager):
		mock_instance = MagicMock()
		mock_superManager.getInstance.return_value = mock_instance
		mock_instance.commonsManager.getFunctionCaller.return_value = 'unittest'
		stateManager = StateManager()

		stateManager.register('unit.test.is.awesome')
		stateManager.register('alice.also')

		state1 = State('awesome')
		state2 = State('also')
		mockStates = [
			state1,
			state2
		]

		stateManager.onStop()
		state1.setState(StateType.STOPPED)
		state2.setState(StateType.STOPPED)

		states = stateManager.allStates()
		self.assertListEqual(states, mockStates)



if __name__ == '__main__':
	unittest.main()
