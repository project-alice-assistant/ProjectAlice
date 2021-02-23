import json
from pathlib import Path

import tempfile

import shutil

from core.base.model.ProjectAliceObject import ProjectAliceObject


class Wakeword(ProjectAliceObject):

	"""
	A wakeword is a hotword that is unique to the user. We can identify a user with it
	"""

	def __init__(self, username: str):
		super().__init__()
		self._rawSamples = dict()
		self._trimmedSamples = dict()
		self._username = username
		self._rootPath = Path(f'{tempfile.gettempdir()}/wakewords/{self._username}')
		self.clearTmp()


	def clearTmp(self):
		"""
		Removes temporary capture directories and samples
		:return:
		"""
		shutil.rmtree(self._rootPath, ignore_errors=True)
		self._rootPath.mkdir(parents=True)


	@property
	def rootPath(self) -> Path:
		return self._rootPath


	@property
	def username(self) -> str:
		return self._username


	@username.setter
	def username(self, value: str):
		self._username = value


	@property
	def rawSamples(self) -> dict:
		return self._rawSamples


	@property
	def trimmedSamples(self) -> dict:
		return self._trimmedSamples


	def addRawSample(self, filepath: Path, sampleNumber: int = None) -> Path:
		"""
		Adds a raw sample. A raw sample is a wav file that wasn't trimmed
		:param filepath:
		:param sampleNumber: If not defined, added to the dict
		:return:
		"""
		if not sampleNumber:
			sampleNumber = self.highestKey(self._rawSamples) + 1

		tmpFile = Path(f'{self._rootPath}/{sampleNumber}_raw.wav')
		shutil.copyfile(filepath, tmpFile)

		self._rawSamples[sampleNumber] = tmpFile
		return tmpFile


	def addTrimmedSample(self, filepath: Path, sampleNumber: int = None) -> Path:
		"""
		Adds a trimmed sample. A trimmed sample is a raw sample that was trimmed
		:param filepath:
		:param sampleNumber: If not defined, added to the dict
		:return:
		"""
		if not sampleNumber:
			sampleNumber = self.highestKey(self._trimmedSamples) + 1

		tmpFile = Path(f'{self._rootPath}/{sampleNumber}.wav')
		shutil.copyfile(filepath, tmpFile)

		self._trimmedSamples[sampleNumber] = tmpFile
		return tmpFile


	def getRawSample(self, sampleNumber: int = None) -> Path:
		"""
		Returns a raw sample. A raw sample is a wav file that wasn't trimmed
		:param sampleNumber: If not defined, returns the last sample
		:return:
		"""
		if not sampleNumber:
			sampleNumber = self.highestKey(self._rawSamples)

		return self._rawSamples[sampleNumber]


	def getTrimmedSample(self, sampleNumber: int = None) -> Path:
		"""
		Returns a trimmed sample. A trimmed sample is a raw sample that was trimmed
		:param sampleNumber: If not defined, returns the last sample
		:return:
		"""
		if not sampleNumber:
			sampleNumber = self.highestKey(self._trimmedSamples)

		return self._trimmedSamples[sampleNumber]


	def removeRawSample(self, sampleNumber: int = None):
		"""
		Removes a raw sample
		:param sampleNumber: if not defined, last entry
		:return:
		"""
		if not sampleNumber:
			sampleNumber = self.highestKey(self._rawSamples)

		self._rawSamples.pop(sampleNumber, None)


	def removeTrimmedSample(self, sampleNumber: int = None):
		"""
		Removes a trimmed sample
		:param sampleNumber: if not defined, last entry
		:return:
		"""
		if not sampleNumber:
			sampleNumber = self.highestKey(self._trimmedSamples)

		self._trimmedSamples.pop(sampleNumber, None)


	def save(self) -> Path:
		"""
		Save this wakeword to disk
		:return: Path to the saved directory
		"""
		config = {
			'hotword_key'            : self._username.lower(),
			'kind'                   : 'personal',
			'dtw_ref'                : 0.22,
			'from_mfcc'              : 1,
			'to_mfcc'                : 13,
			'band_radius'            : 10,
			'shift'                  : 10,
			'window_size'            : 10,
			'sample_rate'            : self.AudioServer.SAMPLERATE,
			'frame_length_ms'        : 25.0,
			'frame_shift_ms'         : 10.0,
			'num_mfcc'               : 13,
			'num_mel_bins'           : 13,
			'mel_low_freq'           : 20,
			'cepstral_lifter'        : 22.0,
			'dither'                 : 0.0,
			'window_type'            : 'povey',
			'use_energy'             : False,
			'energy_floor'           : 0.0,
			'raw_energy'             : True,
			'preemphasis_coefficient': 0.97,
			'model_version'          : 1
		}

		path = Path(self.Commons.rootDir(), 'trained/hotwords/snips_hotword', self._username.lower())

		if path.exists():
			self.logWarning('Destination directory for new wakeword already exists, deleting')
			shutil.rmtree(path)

		path.mkdir()

		(path / 'config.json').write_text(json.dumps(config, indent='\t'))

		for sampleNumber, sample in self._trimmedSamples.items():
			shutil.move(sample, path / f'{int(sampleNumber)}.wav')

		return path


	@staticmethod
	def highestKey(dictionary: dict) -> int:
		"""
		Returns the highest sample number in a given sample dictionary
		:param dictionary: samples
		:return: int
		"""
		i = 0

		if not dictionary:
			return i

		for key, value in dictionary.items():
			if int(key) > i:
				i = key

		return i
