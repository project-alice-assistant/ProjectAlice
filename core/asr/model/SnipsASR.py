from core.asr.model.ASR import ASR


class SnipsASR(ASR):
	NAME = 'Snips ASR'


	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = False
