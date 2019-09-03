from enum import Enum


class NLUTrainingStatus:

	def __init__(self, data: dict):
		if not 'nluStatus' in data:
			raise Exception('NLU status missing in Snips answer')

		data = data['nluStatus']

		self._inProgress = data.get('inProgress', False)
		self._needTraining = data.get('needTraining', False)
		self._trainingResult = data.get('trainingResult', 'ok')


	@property
	def inProgress(self) -> bool:
		return self._inProgress


	@property
	def needTraining(self) -> bool:
		return self._needTraining


	@property
	def trainingResult(self) -> str:
		return self._trainingResult


class ASRTrainingStatus:

	def __init__(self, data: dict):
		if not 'nluStatus' in data:
			raise Exception('ASR status missing in Snips answer')

		data = data['asrStatus']

		self._inProgress = data.get('inProgress', False)
		self._needTraining = data.get('needTraining', False)
		self._trainingResult = data.get('trainingResult', 'ok')


	@property
	def inProgress(self) -> bool:
		return self._inProgress


	@property
	def needTraining(self) -> bool:
		return self._needTraining


	@property
	def trainingResult(self) -> str:
		return self._trainingResult


class TrainingStatusResponse:
	def __init__(self, data: dict):
		self._nluStatus = NLUTrainingStatus(data)
		self._asrStatus = ASRTrainingStatus(data)
		self._approximateDownloadSize = data['approximateDownloadSize'] if 'approximateDownloadSize' in data else -1


	@property
	def nluStatus(self) -> NLUTrainingStatus:
		return self._nluStatus


	@property
	def asrStatus(self) -> ASRTrainingStatus:
		return self._asrStatus


	@property
	def approximateDownloadSize(self) -> int:
		return self._approximateDownloadSize


class SnipsTrainingType(Enum):
	ASR = 'asr'
	NLU = 'nlu'
