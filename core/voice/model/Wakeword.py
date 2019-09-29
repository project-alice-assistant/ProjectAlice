import wave
from pathlib import Path

import tempfile


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


	def newSample(self):
		self.samples.append(wave.open(str(self.getSamplePath(len(self.samples) + 1)), 'wb'))


	def getSamplePath(self, number: int = None) -> Path:
		if not number:
			number = len(self.samples) - 1

		return Path(tempfile.gettempdir(), '{}_raw.wav'.format(number))


	def getSample(self, number: int = None) -> wave.Wave_write:
		if not number:
			number = len(self.samples) - 1

		return self.samples[number]