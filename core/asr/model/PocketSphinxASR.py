from core.asr.model.ASR import ASR


class PocketSphinxASR(ASR):

	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._buffer = list


	def onAudioFrame(self):
		pass


	@staticmethod
	def onListen() -> str:
		pass
