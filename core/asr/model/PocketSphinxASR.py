from typing import Optional

from pocketsphinx import Decoder

from core.asr.model.ASR import ASR
from core.asr.model.ASRResult import ASRResult
from core.asr.model.Recorder import Recorder
from core.util.Stopwatch import Stopwatch


class PocketSphinxASR(ASR):
	NAME = 'Pocketsphinx ASR'


	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = False
		self._decoder: Optional[Decoder] = None


	def onStart(self):
		config = Decoder.default_config()
		config.set_string('-hmm', f'{self.Commons.rootDir()}/venv/lib/python3.7/site-packages/pocketsphinx/model/en-us')
		config.set_string('-lm', f'{self.Commons.rootDir()}/venv/lib/python3.7/site-packages/pocketsphinx/model/en-us.lm.bin')
		config.set_string('-dict', f'{self.Commons.rootDir()}/venv/lib/python3.7/site-packages/pocketsphinx/model/cmudict-en-us.dict')
		self._decoder = Decoder(config)


	def decodeStream(self, recorder: Recorder) -> ASRResult:
		super().decodeStream(recorder)

		i = 0
		self._decoder.start_utt()
		inSpeech = False
		with Stopwatch() as processingTime:
			while recorder.isRecording:
				if self._timeout.isSet():
					break

				frame = recorder.getFrame(i)
				if not frame:
					continue

				i += 1

				self._decoder.process_raw(frame, False, False)
				if self._decoder.get_in_speech() != inSpeech:
					inSpeech = self._decoder.get_in_speech()
					if not inSpeech:
						self._decoder.end_utt()
						recorder.stopRecording()
						result = self._decoder.hyp() if self._decoder.hyp() else None

		return ASRResult(
			text=result.hypstr.strip(),
			session=recorder.session,
			likelihood=result.get_logmath().exp(self._decoder.hyp().prob),
			processingTime=processingTime.time
		) if result else None
