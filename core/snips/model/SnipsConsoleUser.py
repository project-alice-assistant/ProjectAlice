# -*- coding: utf-8 -*-


class SnipsConsoleUser:

	def __init__(self, data):
		self._userId = data['id']
		self._userEmail = data['email']


	@property
	def userId(self) -> str:
		return self._userId


	@property
	def userEmail(self) -> str:
		return self._userEmail