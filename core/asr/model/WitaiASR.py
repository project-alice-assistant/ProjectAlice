# https://wit.ai/docs/http/20170307#streaming-audio

from wit import Wit

from core.asr.model.ASR import ASR
from core.asr.model.ASRResult import ASRResult
from core.asr.model.Recorder import Recorder
from core.dialog.model.DialogSession import DialogSession


class WitaiASR(ASR):
	DEPENDENCIES = [
		'wit==5.1.0'
	]


	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = True
		self._client = None


	def onStart(self):
		self._client = Wit('token')


	def install(self) -> bool:
		return super().install()


	def decodeStream(self, session: DialogSession) -> ASRResult:
		super().decodeStream(session)
		recorder = Recorder(self._timeout)
		self.ASRManager.addRecorder(session.siteId, recorder)
		with recorder as stream:
			audioStream = stream.audioStream()

			for chunk in audioStream:
				response = self._client.speech(chunk, None, {'Content-type': 'audio/wav', 'Transfer-encoding': 'chunked'})

		self.end(recorder, session)

		return ASRResult(
			text='',
			session=session,
			likelihood=1,
			processingTime=10
		) if '' else None
