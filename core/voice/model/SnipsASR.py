from core.voice.model.ASR import ASR


class SnipsASR(ASR):

	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = False
