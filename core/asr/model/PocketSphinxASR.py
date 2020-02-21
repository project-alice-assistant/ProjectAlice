from pathlib import Path
from typing import Optional

import shutil
import tarfile

from core.asr.model.ASR import ASR
from core.asr.model.ASRResult import ASRResult
from core.asr.model.Recorder import Recorder
from core.dialog.model.DialogSession import DialogSession
from core.util.Stopwatch import Stopwatch

try:
	from pocketsphinx import Decoder
except:
	pass


class PocketSphinxASR(ASR):
	NAME = 'Pocketsphinx ASR'
	DEPENDENCIES = {
		'system': [
			'swig',
			'libpulse-dev'
		],
		'pip'   : [
			'pocketsphinx==0.1.15'
		]
	}

	LANGUAGE_PACKS = {
		'fr': {
			'cmusphinx-fr-ptm-8khz-5.2': 'https://sourceforge.net/projects/cmusphinx/files/Acoustic%20and%20Language%20Models/French/cmusphinx-fr-ptm-8khz-5.2.tar.gz/download',
			'cmudict-fr-fr.dict'       : 'https://sourceforge.net/projects/cmusphinx/files/Acoustic%20and%20Language%20Models/French/fr.dict/download',
			'fr-fr.lm.bin'             : 'https://sourceforge.net/projects/cmusphinx/files/Acoustic%20and%20Language%20Models/French/fr-small.lm.bin/download'
		},
		'de': {
			'cmusphinx-de-voxforge-5.2': 'https://sourceforge.net/projects/cmusphinx/files/Acoustic%20and%20Language%20Models/German/cmusphinx-de-voxforge-5.2.tar.gz/download',
			'cmudict-de-de.dict'       : 'https://sourceforge.net/projects/cmusphinx/files/Acoustic%20and%20Language%20Models/German/cmusphinx-voxforge-de.dic/download',
			'de-de.lm.bin'             : 'https://sourceforge.net/projects/cmusphinx/files/Acoustic%20and%20Language%20Models/German/cmusphinx-voxforge-de.lm.bin/download',
		}
	}


	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = False
		self._decoder: Optional[Decoder] = None
		self._config = None


	def onStart(self):
		super().onStart()

		if not self.checkLanguage():
			self.downloadLanguage()

		self._config = Decoder.default_config()
		self._config.set_string('-hmm', f'{self.Commons.rootDir()}/venv/lib/python3.7/site-packages/pocketsphinx/model/{self.LanguageManager.activeLanguageAndCountryCode.lower()}')
		self._config.set_string('-lm', f'{self.Commons.rootDir()}/venv/lib/python3.7/site-packages/pocketsphinx/model/{self.LanguageManager.activeLanguageAndCountryCode.lower()}.lm.bin')
		self._config.set_string('-dict', f'{self.Commons.rootDir()}/venv/lib/python3.7/site-packages/pocketsphinx/model/cmudict-{self.LanguageManager.activeLanguageAndCountryCode.lower()}.dict')
		self._decoder = Decoder(self._config)


	def checkLanguage(self) -> bool:
		if not Path(self.Commons.rootDir(), f'venv/lib/python3.7/site-packages/pocketsphinx/model/{self.LanguageManager.activeLanguageAndCountryCode.lower()}').exists():
			self.logInfo('Missing language model')
			return False

		return True


	def downloadLanguage(self) -> bool:
		self.logInfo(f'Downloading language model for {self.LanguageManager.activeLanguage}')

		venv = Path(self.Commons.rootDir(), 'venv/lib/python3.7/site-packages/pocketsphinx/')
		for filename, url in self.LANGUAGE_PACKS[self.LanguageManager.activeLanguage].items():
			download = Path(venv, 'model', filename)
			self.Commons.downloadFile(url=url, dest=str(download))

			if filename.endswith('.tar.gz'):
				dest = Path(venv, 'model', self.LanguageManager.activeLanguageAndCountryCode.lower())

				if dest.exists():
					shutil.rmtree(dest)

				tar = tarfile.open(str(download))
				tar.extractall(str(download).replace('.tar.gz', ''))

		# Path(venv, 'model', filename).rename(dest)

		self.logInfo('Downloaded and installed')
		return True


	def decodeStream(self, session: DialogSession) -> Optional[ASRResult]:
		super().decodeStream(session)

		result = None
		with Stopwatch() as processingTime:
			with Recorder(self._timeout) as recorder:
				self.ASRManager.addRecorder(session.siteId, recorder)
				self._decoder.start_utt()
				inSpeech = False
				for chunk in recorder:
					if self._timeout.isSet():
						break

					self._decoder.process_raw(chunk, False, False)
					if self._decoder.get_in_speech() != inSpeech:
						inSpeech = self._decoder.get_in_speech()
						if not inSpeech:
							self._decoder.end_utt()
							result = self._decoder.hyp() if self._decoder.hyp() else None
							break

				self.end(recorder, session)

		return ASRResult(
			text=result.hypstr.strip(),
			session=session,
			likelihood=self._decoder.hyp().prob,
			processingTime=processingTime.time
		) if result else None
