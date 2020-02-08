import typing

from pocketsphinx import Ad, Decoder, Pocketsphinx

from core.asr.model.ASR import ASR


class PocketSphinxASR(ASR):

	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._decoder: typing.Optional[Decoder] = None
		self._buffer = bytearray(2048)
		self._pocketsphinx = Pocketsphinx()
		self._ad = Ad()


	def onStart(self):
		pass


	def onListen(self) -> str:
		with self._ad:
			with self._pocketsphinx.start_utterance():
				while self._ad.readinto(self._buffer) >= 0:
					print('buffer processing')
					self._pocketsphinx.process_raw(self._buffer, True, False)
					if not self._pocketsphinx.get_in_speech() and self._pocketsphinx.hyp():
						with self._pocketsphinx.end_utterance():
							return self._pocketsphinx.hyp().hypstr.strip()
