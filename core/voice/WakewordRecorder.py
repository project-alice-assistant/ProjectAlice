import shutil
from enum import Enum
from pathlib import Path
from typing import Optional

from pydub import AudioSegment

from core.base.model.Manager import Manager
from core.commons import constants
from core.device.model.DeviceAbility import DeviceAbility
from core.dialog.model.DialogSession import DialogSession
from core.voice.model.Wakeword import Wakeword
from core.voice.model.WakewordUploadThread import WakewordUploadThread


class WakewordRecorderState(Enum):
	IDLE = 1
	RECORDING = 2
	VALIDATING = 3
	CONFIRMING = 4
	TRIMMING = 5
	FINALIZING = 6


class WakewordRecorder(Manager):

	def __init__(self):
		super().__init__()

		self._state = WakewordRecorderState.IDLE

		self._audio = None
		self._wakeword: Optional[Wakeword] = None
		self._userTuning = 0
		self._wakewordUploadThreads = list()
		self._sampleRate = self.AudioServer.SAMPLERATE
		self._channels = 1
		self._gainFix = 0


	def onStart(self):
		super().onStart()
		self._sampleRate = self.AudioServer.SAMPLERATE


	def onStop(self):
		super().onStop()

		for thread in self._wakewordUploadThreads:
			if thread.isAlive():
				thread.join(timeout=2)


	def onCaptured(self, session: DialogSession):
		if self.state == WakewordRecorderState.RECORDING:
			self._workAudioFile()


	def newWakeword(self, username: str):
		self._wakeword = Wakeword(username)


	def cancelWakeword(self):
		self.state = WakewordRecorderState.IDLE
		if self._wakeword:
			self._wakeword.clearTmp()

		self._wakeword = None


	def startCapture(self):
		self.DialogManager.disableCaptureChime()
		self._state = WakewordRecorderState.RECORDING


	def addRawSample(self, filepath: Path) -> Path:
		filepath = self.wakeword.addRawSample(filepath)
		self._workAudioFile(filepath)
		return filepath


	def getRawSample(self, sampleNumber: int = None):
		return self.wakeword.getRawSample(sampleNumber)


	def getTrimmedSample(self, sampleNumber: int = None):
		return self.wakeword.getTrimmedSample(sampleNumber)


	def _workAudioFile(self, filepath: Path = None):
		self._state = WakewordRecorderState.TRIMMING

		if not filepath:
			filepath = self.wakeword.getRawSample()

		sound = AudioSegment.from_file(filepath, format='wav')

		if self._gainFix > 0:
			sound.append(self._gainFix)

		startTrim = self.detectLeadingSilence(sound)
		endTrim = self.detectLeadingSilence(sound.reverse())
		duration = len(sound)
		trimmed = sound[startTrim: duration - endTrim]

		reworked = trimmed.set_frame_rate(self.AudioServer.SAMPLERATE)
		reworked = reworked.set_channels(1)

		tempFile = Path(filepath.parent, 'tmp.wav')
		if tempFile.exists():
			tempFile.unlink()

		reworked.export(tempFile, format='wav')

		self._wakeword.addTrimmedSample(tempFile, int(filepath.stem.replace('_raw', '')))
		self._state = WakewordRecorderState.CONFIRMING


	def getLastSampleNumber(self) -> int:
		if self._wakeword and self._wakeword.getTrimmedSample():
			return len(self._wakeword.trimmedSamples.keys())
		return 1


	def trimMore(self):
		self._userTuning += 3
		self._workAudioFile()


	def trimLess(self):
		self._userTuning -= 2
		self._workAudioFile()


	def detectLeadingSilence(self, sound: AudioSegment) -> int:
		average = sound.dBFS
		pos = 0
		while sound[pos: pos + 10].dBFS < (average + self._userTuning) and pos < len(sound):
			pos += 10

		return pos


	def tryCaptureFix(self):
		self._sampleRate /= 2
		self._channels = 1


	def removeRawSample(self, sampleNumber: int = None):
		self._wakeword.removeRawSample(sampleNumber)


	def finalizeWakeword(self):
		self.logInfo(f'Finalyzing wakeword')
		self._state = WakewordRecorderState.FINALIZING
		path = self._wakeword.save()
		self.ThreadManager.newThread(name='SatelliteWakewordUpload', target=self._upload, args=[path, self._wakeword.username], autostart=True)
		self.cancelWakeword()
		self.WakewordManager.restartEngine()


	def uploadToNewDevice(self, uid: str):
		directory = Path(self.Commons.rootDir(), 'trained/hotwords/snips_hotword')
		for fiile in directory.iterdir():
			if (directory / fiile).is_file():
				continue

			self._upload(directory / fiile, uid)


	def _upload(self, path: Path, uid: str = ''):
		wakewordName, zipPath = self._prepareHotword(path)

		for device in self.DeviceManager.getDevicesWithAbilities(abilities=[DeviceAbility.CAPTURE_SOUND], connectedOnly=True):
			if uid and device.uid != uid:
				continue

			port = 8600 + len(self._wakewordUploadThreads)

			payload = {
				'ip'  : self.Commons.getLocalIp(),
				'port': port,
				'name': wakewordName
			}

			if uid:
				payload['uid'] = uid

			self.MqttManager.publish(topic=constants.TOPIC_NEW_HOTWORD, payload=payload)
			thread = WakewordUploadThread(host=self.Commons.getLocalIp(), zipPath=zipPath, port=port)
			self._wakewordUploadThreads.append(thread)
			thread.start()


	def _prepareHotword(self, path: Path) -> tuple:
		wakewordName = path.name
		zipPath = path.parent / (wakewordName + '.zip')

		self.logInfo(f'Cleaning up {wakewordName}')
		if zipPath.exists():
			zipPath.unlink()

		self.logInfo(f'Packing wakeword {wakewordName}')
		shutil.make_archive(base_name=zipPath.with_suffix(''), format='zip', root_dir=str(path))

		return wakewordName, zipPath


	def getUserWakeword(self, username: str) -> Optional[str]:
		wakeword = Path(f'{self.Commons.rootDir()}/trained/hotwords/snips_hotword/{username}')
		if not wakeword.exists():
			return None
		return wakeword


	def getUserWakewordSensitivity(self, username: str) -> Optional[float]:
		# TODO user wakeword sensitivity
		return self.ConfigManager.getAliceConfigByName('wakewordSensitivity')


	def setUserWakewordSensitivity(self, username: str, sensitivity: float) -> bool:
		# TODO user wakeword sensitivity
		return True


	# wakewords = self.ConfigManager.getSnipsConfiguration(parent='snips-hotword', key='model')
	# rebuild = list()
	#
	# if sensitivity > 1:
	# 	sensitivity = 1
	# elif sensitivity < 0:
	# 	sensitivity = 0
	#
	# usernameMatch = re.compile(f'.*/{username}=[0-9.]+$')
	# sensitivitySub = re.compile('=[0-9.]+$')
	# update = False
	# for wakeword in wakewords:
	# 	match = re.search(usernameMatch, wakeword)
	# 	if not match:
	# 		rebuild.append(wakeword)
	# 		continue
	#
	# 	update = True
	# 	updated = re.sub(sensitivitySub, f'={round(float(sensitivity), 2)}', wakeword)
	# 	rebuild.append(updated)
	#
	# 	self.WakewordManager.restartEngine()
	#
	# return update


	@property
	def state(self) -> WakewordRecorderState:
		return self._state


	@state.setter
	def state(self, value: WakewordRecorderState):
		self._state = value


	@property
	def wakeword(self) -> Wakeword:
		return self._wakeword
