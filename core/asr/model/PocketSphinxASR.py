from pathlib import Path
from threading import Event
from typing import Optional

from pocketsphinx import Decoder

from core.asr.model.ASR import ASR
from core.asr.model.ASRResult import ASRResult
from core.asr.model.Recorder import Recorder
from core.dialog.model.DialogSession import DialogSession
from core.util.Stopwatch import Stopwatch


class PocketSphinxASR(ASR):
	NAME = 'Pocketsphinx ASR'


	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = False
		self._decoder: Optional[Decoder] = None
		self._timeoutFlag = Event()


	def onStart(self):
		config = Decoder.default_config()
		config.set_string('-hmm', f'{self.Commons.rootDir()}/venv/lib/python3.7/site-packages/pocketsphinx/model/en-us')
		config.set_string('-lm', f'{self.Commons.rootDir()}/venv/lib/python3.7/site-packages/pocketsphinx/model/en-us.lm.bin')
		config.set_string('-dict', f'{self.Commons.rootDir()}/venv/lib/python3.7/site-packages/pocketsphinx/model/cmudict-en-us.dict')
		self._decoder = Decoder(config)


	def decodeStream(self, recorder: Recorder):
		self._timeoutFlag.clear()
		self.ThreadManager.doLater(interval=15, func=self.timeout)

		i = 0
		self._decoder.start_utt()
		inSpeech = False
		while recorder.isRecording:
			if self._timeoutFlag.isSet():
				break

			chunk = recorder.getChunk(i)
			if not chunk:
				continue

			i += 1

			self._decoder.process_raw(chunk, False, False)
			if self._decoder.get_in_speech() != inSpeech:
				inSpeech = self._decoder.get_in_speech()
				if not inSpeech:
					self._decoder.end_utt()
					recorder.stopRecording()
					return self._decoder.hyp()


	def timeout(self):
		self._timeoutFlag.set()


	def decodeFile(self, filepath: Path, session: DialogSession) -> ASRResult:
		with Stopwatch() as processingTime:
			self._decoder.start_utt()
			stream = filepath.open('rb')
			while True:
				buf = stream.read(1024)
				if not buf:
					break

				self._decoder.process_raw(buf, True, False)
			self._decoder.end_utt()

		return ASRResult(
			text=self._decoder.hyp().hypstr.strip(),
			session=session,
			likelihood=self._decoder.get_logmath().exp(self._decoder.hyp().prob),
			processingTime=processingTime.time
		)
