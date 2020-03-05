from pathlib import Path
from typing import Generator, Optional

import numpy as np
import tarfile

from core.asr.model.ASR import ASR
from core.asr.model.ASRResult import ASRResult
from core.asr.model.Recorder import Recorder
from core.dialog.model.DialogSession import DialogSession
from core.util.Stopwatch import Stopwatch

try:
	import deepspeech
	import webrtcvad
except:
	pass


class DeepSpeechASR(ASR):
	NAME = 'DeepSpeech ASR'
	DEPENDENCIES = {
		'system': [],
		'pip'   : {
			'deepspeech==0.6.1',
			'webrtcvad==2.0.10'
		}
	}


	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = False

		self._model: Optional[deepspeech.Model] = None
		self._vad: Optional[webrtcvad.Vad] = None
		self._triggerFlag = self.ThreadManager.newEvent('asrTriggerFlag')


	def onStart(self):
		super().onStart()
		self._model = deepspeech.Model('/home/pi/deepspeech-0.6.1-models/output_graph.tflite', 500)
		self._model.enableDecoderWithLM('/home/pi/deepspeech-0.6.1-models/lm.binary', '/home/pi/deepspeech-0.6.1-models/trie', 0.75, 1.85)
		self._vad = webrtcvad.Vad()
		self._vad.set_mode(1)


	def install(self) -> bool:
		super().install()
		try:
			url = 'https://github.com/mozilla/DeepSpeech/releases/download/v0.6.1/deepspeech-0.6.1-models.tar.gz'
			self.Commons.downloadFile(url, str(Path(self.Commons.rootDir(), 'var/voices', url.rsplit('/')[-1])))
			tar = tarfile.open(str(Path(self.Commons.rootDir(), url.rsplit('/')[-1])))
			tar.extractall()
			return True
		except Exception as e:
			self.logError(f'Error installing dependencies: {e}')
			return False


	def onVadUp(self):
		if not self._triggerFlag.is_set():
			self._triggerFlag.set()


	def onVadDown(self):
		if self._triggerFlag.is_set():
			self._triggerFlag.clear()


	def decodeStream(self, session: DialogSession) -> Optional[ASRResult]:
		super().decodeStream(session)
		with Stopwatch() as processingTime:
			with Recorder(self._timeout) as recorder:
				self.ASRManager.addRecorder(session.siteId, recorder)
				self._recorder = recorder
				streamContext = self._model.createStream()
				triggered = False
				for chunk in recorder:
					if self._timeout.isSet():
						break

					self._model.feedAudioContent(streamContext, np.frombuffer(chunk, np.int16))

					result = self._model.intermediateDecode(streamContext)
					self.partialTextCaptured(session=session, text=result, likelihood=1, seconds=0)

					if not triggered and self._triggerFlag.is_set():
						triggered = True

					if triggered and not self._triggerFlag.is_set():
						recorder.stopRecording()

				text = self._model.finishStream(streamContext)
				self.end(session)

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
