import unittest
from unittest import mock
from unittest.mock import MagicMock, PropertyMock

from requests.exceptions import RequestException

from core.util.InternetManager import InternetManager


class TestInternetManager(unittest.TestCase):

	@mock.patch('core.util.InternetManager.Manager.broadcast')
	@mock.patch('core.util.InternetManager.requests')
	@mock.patch('core.util.InternetManager.InternetManager.Commons', new_callable=PropertyMock)
	def test_checkOnlineState(self, mock_commons, mock_requests, mock_broadcast):
		common_mock = MagicMock()
		common_mock.getFunctionCaller.return_value = 'InternetManager'
		mock_commons.return_value = common_mock

		internetManager = InternetManager()

		# request returns status code 204
		mock_requestsResult = MagicMock()
		mock_statusCode = mock.PropertyMock(return_value=204)
		type(mock_requestsResult).status_code = mock_statusCode
		mock_requests.get.return_value = mock_requestsResult

		internetManager.checkOnlineState()
		mock_requests.get.assert_called_once_with('https://clients3.google.com/generate_204')
		mock_broadcast.assert_called_once_with(method='internetConnected', exceptions=['InternetManager'], propagateToSkills=True)
		self.assertEqual(internetManager.online, True)
		mock_broadcast.reset_mock()
		mock_requests.reset_mock()

		# when calling check online state a second time it does not broadcast again
		internetManager.checkOnlineState()
		mock_requests.get.assert_called_once_with('https://clients3.google.com/generate_204')
		mock_broadcast.assert_not_called()
		self.assertEqual(internetManager.online, True)
		mock_broadcast.reset_mock()
		mock_requests.reset_mock()

		# request returns status code 400
		mock_requestsResult = MagicMock()
		mock_statusCode = mock.PropertyMock(return_value=400)
		type(mock_requestsResult).status_code = mock_statusCode
		mock_requests.get.return_value = mock_requestsResult

		# when wrong status code is returned (and currently online)
		internetManager.checkOnlineState()
		mock_requests.get.assert_called_once_with('https://clients3.google.com/generate_204')
		mock_broadcast.assert_called_once_with(method='internetLost', exceptions=['InternetManager'], propagateToSkills=True)
		self.assertEqual(internetManager.online, False)
		mock_broadcast.reset_mock()
		mock_requests.reset_mock()

		# when calling check online state a second time it does not broadcast again
		internetManager.checkOnlineState()
		mock_requests.get.assert_called_once_with('https://clients3.google.com/generate_204')
		mock_broadcast.assert_not_called()
		self.assertEqual(internetManager.online, False)
		mock_broadcast.reset_mock()
		mock_requests.reset_mock()

		# set state to online again
		mock_requestsResult = MagicMock()
		mock_statusCode = mock.PropertyMock(return_value=204)
		type(mock_requestsResult).status_code = mock_statusCode
		mock_requests.get.return_value = mock_requestsResult
		internetManager.checkOnlineState()
		mock_broadcast.reset_mock()
		mock_requests.reset_mock()

		# request raises exception is the same as non 204 status code
		mock_requests.get.side_effect = RequestException
		internetManager.checkOnlineState()
		mock_requests.get.assert_called_once_with('https://clients3.google.com/generate_204')
		mock_broadcast.assert_called_once_with(method='internetLost', exceptions=['InternetManager'], propagateToSkills=True)
		self.assertEqual(internetManager.online, False)


if __name__ == "__main__":
	unittest.main()
