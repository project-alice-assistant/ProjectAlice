import threading
from pathlib import Path
from typing import Generator, Optional

import numpy as np

from core.asr.model.ASRResult import ASRResult
from core.asr.model.Asr import Asr
from core.asr.model.Recorder import Recorder
from core.dialog.model.DialogSession import DialogSession
from core.util.Stopwatch import Stopwatch

try:
	import deepspeech
except:
	pass


class DeepSpeechAsr(Asr):
	NAME = 'DeepSpeech Asr'
	DEPENDENCIES = {
		'system': [],
		'pip'   : {
			'deepspeech==0.6.1'
		}
	}


	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = False

		self._langPath = Path(self.Commons.rootDir(), f'trained/asr/deepspeech/{self.LanguageManager.activeLanguage}')

		self._model: Optional[deepspeech.Model] = None
		self._triggerFlag = self.ThreadManager.newEvent('asrTriggerFlag')
		self._vadTemporisation: Optional[threading.Timer] = None


	def onStart(self):
		super().onStart()

		if not self.checkLanguage():
			self.downloadLanguage()

		self._model = deepspeech.Model(f'{self._langPath}/deepspeech-0.6.1-models/output_graph.tflite', 500)
		self._model.enableDecoderWithLM(f'{self._langPath}/deepspeech-0.6.1-models/lm.binary', f'{self._langPath}/deepspeech-0.6.1-models/trie', 0.75, 1.85)


	def install(self) -> bool:
		super().install()
		return self.downloadLanguage() if not self.checkLanguage() else True


	def checkLanguage(self) -> bool:
		if not self._langPath.exists():
			self._langPath.mkdir(parents=True)
			return False

		return False if not (self._langPath / 'deepspeech-0.6.1-models/output_graph.tflite').exists() else True


	def downloadLanguage(self) -> bool:
		self.logInfo(f'Downloading language model for "{self.LanguageManager.activeLanguage}", hold on, this is going to take some time!')
		url = 'https://github.com/mozilla/DeepSpeech/releases/download/v0.6.1/deepspeech-0.6.1-models.tar.gz'

		downloadPath = (self._langPath / url.rsplit('/')[-1])
		try:
			self.Commons.downloadFile(url, str(downloadPath))

			self.logInfo(f'Language model for "{self.LanguageManager.activeLanguage}" downloaded, now extracting...')
			self.Commons.runSystemCommand(['tar', '-C', f'{str(downloadPath.parent)}', '-zxvf', str(downloadPath)])

			downloadPath.unlink()
			return True
		except Exception as e:
			self.logError(f'Error installing language model: {e}')
			downloadPath.unlink()
			return False


	def onVadUp(self):
		self._triggerFlag.set()


	def onVadDown(self):
		if not self._triggerFlag.is_set():
			return

		self._recorder.stopRecording()


	def decodeStream(self, session: DialogSession) -> Optional[ASRResult]:
		super().decodeStream(session)
		result = None
		previous = ''

		with Stopwatch() as processingTime:
			with Recorder(self._timeout, session.user, session.siteId) as recorder:
				self.ASRManager.addRecorder(session.siteId, recorder)
				self._recorder = recorder
				streamContext = self._model.createStream()
				for chunk in recorder:
					if not chunk:
						break

					self._model.feedAudioContent(streamContext, np.frombuffer(chunk, np.int16))

					result = self._model.intermediateDecode(streamContext)
					if result and result != previous:
						previous = result
						self.partialTextCaptured(session=session, text=result, likelihood=1, seconds=0)

			text = self._model.finishStream(streamContext)
			self._triggerFlag.clear()
			self.end()

		return ASRResult(
			text=text,
			session=session,
			likelihood=1.0,
			processingTime=processingTime.time
		) if result else None


	def _checkResponses(self, session: DialogSession, responses: Generator) -> Optional[tuple]:
		if responses is None:
			return None

		for response in responses:
			if not response.results:
				continue

			result = response.results[0]
			if not result.alternatives:
				continue

			if result.is_final:
				return result.alternatives[0].transcript, result.alternatives[0].confidence
			else:
				self.partialTextCaptured(session=session, text=result.alternatives[0].transcript, likelihood=result.alternatives[0].confidence, seconds=0)

		return None
