import json
import os
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import Optional

from core.asr.model.ASRResult import ASRResult
from core.asr.model.Asr import Asr
from core.asr.model.Recorder import Recorder
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.util.Stopwatch import Stopwatch

try:
	from vosk import Model, SpkModel, KaldiRecognizer
except:
	pass


class VoskAsr(Asr):
	NAME = 'Vosk Asr'
	DEPENDENCIES = {
		'system': [],
		'pip'   : [
			'vosk'
		]
	}

	LANGUAGE_PACK = {
		'https://alphacephei.com/kaldi/models/vosk-model-small-%lang%-0.3.zip'
	# 	https://github.com/daanzu/kaldi-active-grammar/releases/download/v1.4.0/vosk-model-%lang%-daanzu-20200328-lgraph.zip
	}


	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = False
		self.rec = None


	def onStart(self):
		super().onStart()

		if not self.checkLanguage():
			self.downloadLanguage()

		self.modelStt = Model(f'{self.Commons.rootDir()}/trained/asr/vosk/model/{self.LanguageManager.activeLanguageAndCountryCode.lower()}')
		# self.modelSpk = Model(f'{self.Commons.rootDir()}/trained/asr/vosk/model/{self.LanguageManager.activeLanguageAndCountryCode.lower()}')

	def checkLanguage(self) -> bool:
		if not Path(self.Commons.rootDir(), f'/trained/asr/vosk/model/{self.LanguageManager.activeLanguageAndCountryCode.lower()}').exists():
			self.logInfo('Missing language model')
			return False

		return True


	def downloadLanguage(self) -> bool:
		self.logInfo(f'Downloading language model for "{self.LanguageManager.activeLanguage}"')

		directory = Path(self.Commons.rootDir(), '/trained/asr/vosk/model/', self.LanguageManager.activeLanguageAndCountryCode.lower())
		for url in self.LANGUAGE_PACK:
			url = url.replace('%lang%', self.LanguageManager.activeLanguageAndCountryCode.lower())
			filename = Path(url).name
			download = Path(directory, filename)
			self.Commons.downloadFile(url=f'{url}', dest=str(download))

			zip_ref = zipfile.ZipFile(str(download))  # create zipfile object
			zip_ref.extractall(directory)  # extract file to dir
			zip_ref.close()  # close file
			# download.unlink()

		self.logInfo('Downloaded and installed')
		return True


	def decodeStream(self, session: DialogSession) -> Optional[ASRResult]:
		super().decodeStream(session)
		result = None
		counter = 0
		partial = ''
		rec = KaldiRecognizer(self.modelStt, self.AudioServer.SAMPLERATE)
		with Stopwatch() as processingTime:
			with Recorder(self._timeout, session.user, session.siteId) as recorder:
				self.ASRManager.addRecorder(session.siteId, recorder)
				self._recorder = recorder
				for chunk in recorder:
					if self._timeout.isSet() or not chunk:
						break
					rec.AcceptWaveform(chunk)
					new = json.loads(rec.PartialResult())['partial']
					if new == partial:
						continue
					partial = new
					self.partialTextCaptured(session=session, text=partial, likelihood=1, seconds=0)
				self.end()
		res = json.loads(rec.FinalResult())
		result = res['text']
		prob = 0
		if 'result' not in res.keys():
			return None
		for data in res['result']:
			prob += data['conf']
		prob = prob / len(res['result'])
		return ASRResult(
			text=result,
			session=session,
			likelihood=prob,
			processingTime=processingTime.time
		) if result else None

	def onVadDown(self):
		self._recorder.stopRecording()
