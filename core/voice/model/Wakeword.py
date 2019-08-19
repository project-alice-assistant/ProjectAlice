# -*- coding: utf-8 -*-

class Wakeword:

	def __init__(self, username: str):
		self._samples = list()
		self._username = username


	@property
	def username(self) -> str:
		return self._username


	@username.setter
	def username(self, value: str):
		self._username = value


	@property
	def samples(self) -> list:
		return self._samples
