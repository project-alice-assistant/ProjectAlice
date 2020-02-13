from pathlib import Path
from typing import Optional

from pocketsphinx import Decoder

from core.asr.model.ASR import ASR
from core.asr.model.ASRResult import ASRResult
from core.dialog.model.DialogSession import DialogSession
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


	def decode(self, filepath: Path, session: DialogSession) -> ASRResult:
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
