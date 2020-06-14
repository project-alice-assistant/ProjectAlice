import wave
from pathlib import Path

import tempfile

from core.base.model.ProjectAliceObject import ProjectAliceObject


class Wakeword(ProjectAliceObject):

	def __init__(self, username: str):
		super().__init__()
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
		sample = wave.open(str(self.getSamplePath(len(self._samples) + 1)), 'wb')
		sample.setsampwidth(2)
		sample.setframerate(self.AudioServer.SAMPLERATE)
		sample.setnchannels(1)
		self._samples.append(sample)


	def getSamplePath(self, number: int = None) -> Path:
		if not number:
			number = len(self._samples)

		return Path(tempfile.gettempdir(), f'{number}_raw.wav')


	def getSample(self, number: int = None) -> wave.Wave_write:
		if not number:
			number = len(self.samples) - 1

		return self.samples[number]
