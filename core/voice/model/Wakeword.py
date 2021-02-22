import os
from pathlib import Path

import tempfile

import shutil

from core.base.model.ProjectAliceObject import ProjectAliceObject


class Wakeword(ProjectAliceObject):

	def __init__(self, username: str):
		super().__init__()
		self._rawSamples = list()
		self._trimmedSamples = list()
		self._username = username
		self._rootPath = Path(f'{tempfile.gettempdir()}/wakewords/{self._username}')
		self.clearTmp()


	def clearTmp(self):
		shutil.rmtree(self._rootPath, ignore_errors=True)
		os.makedirs(self._rootPath)


	@property
	def username(self) -> str:
		return self._username


	@username.setter
	def username(self, value: str):
		self._username = value


	@property
	def samples(self) -> list:
		return self._rawSamples


	def addRawSample(self, filepath: Path) -> Path:
		tmpFile = Path(f'{self._rootPath}/{len(self._rawSamples) + 1}_raw.wav')
		shutil.copyfile(filepath, tmpFile)
		self._rawSamples.append(tmpFile)
		return tmpFile


	def addTrimmedSample(self, filepath: Path, sampleNumber: int = None) -> Path:
		tmpFile = Path(f'{self._rootPath}/{sampleNumber or len(self._trimmedSamples) + 1}.wav')
		shutil.copyfile(filepath, tmpFile)
		self._trimmedSamples.append(tmpFile)
		return tmpFile


	def getRawSample(self, i: int = None) -> Path:
		if not i:
			i = len(self._rawSamples) - 1

		return self._rawSamples[i]


	def getTrimmedSample(self, i: int = None) -> Path:
		if not i:
			i = len(self._trimmedSamples) - 1

		return self._trimmedSamples[i]
