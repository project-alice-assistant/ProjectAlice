import json
import re
import shutil
import struct
import tempfile
from enum import Enum
from pathlib import Path
from typing import Optional

import paho.mqtt.client as mqtt
from pydub import AudioSegment

from core.base.model.Manager import Manager
from core.commons import constants
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

	RECORD_SECONDS = 2.5
	THRESHOLD = -40.0


	def __init__(self):
		super().__init__()

		self._state = WakewordRecorderState.IDLE

		self._audio = None
		self._wakeword = None
		self._threshold = 0
		self._wakewordUploadThreads = list()
		self._sampleRate = self.AudioServer.SAMPLERATE
		self._channels = 1


	def onStart(self):
		super().onStart()
		self._sampleRate = self.AudioServer.SAMPLERATE
		self._threshold = self.THRESHOLD


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


	def startCapture(self):
		self._state = WakewordRecorderState.RECORDING


	def addRawSample(self, filepath: Path):
		filepath = self.wakeword.addRawSample(filepath)
		self._workAudioFile(filepath)


	def getRawSample(self, i: int = None):
		return self.wakeword.getRawSample(i)


	def _workAudioFile(self, filepath: Path = None):
		self._state = WakewordRecorderState.TRIMMING

		if not filepath:
			filepath = self.wakeword.getRawSample()

		# sound = AudioSegment.from_file(filepath, format='wav', frame_rate=self.AudioServer.SAMPLERATE)
		# startTrim = self.detectLeadingSilence(sound)
		# endTrim = self.detectLeadingSilence(sound.reverse())
		# duration = len(sound)
		# trimmed = sound[startTrim: duration - endTrim]
		# reworked = trimmed.set_frame_rate(self.AudioServer.SAMPLERATE)
		# reworked = reworked.set_channels(1)
		# reworked.export(filepath, format='wav')

		self._state = WakewordRecorderState.CONFIRMING







	def trimMore(self):
		self._threshold += 3
		self._workAudioFile()


	def trimLess(self):
		self._threshold -= 2
		self._workAudioFile()


	def detectLeadingSilence(self, sound):
		trim = 0
		while sound[trim: trim + 10].dBFS < self._threshold and trim < len(sound):
			trim += 10
		return trim


	def tryCaptureFix(self):
		self._sampleRate /= 2
		self._channels = 1
		self._state = WakewordRecorderState.IDLE


	def removeSample(self):
		del self._wakeword.samples[-1]


	def isDefaultThreshold(self) -> bool:
		return self._threshold == self.THRESHOLD


	def getLastSampleNumber(self) -> int:
		if self._wakeword and self._wakeword.samples:
			return len(self._wakeword.samples)
		return 1


	def finalizeWakeword(self):
		self.logInfo(f'Finalyzing wakeword')
		self._state = WakewordRecorderState.FINALIZING

		config = {
			'hotword_key': self._wakeword.username.lower(),
			'kind': 'personal',
			'dtw_ref': 0.22,
			'from_mfcc': 1,
			'to_mfcc': 13,
			'band_radius': 10,
			'shift': 10,
			'window_size': 10,
			'sample_rate': self.AudioServer.SAMPLERATE,
			'frame_length_ms': 25.0,
			'frame_shift_ms': 10.0,
			'num_mfcc': 13,
			'num_mel_bins': 13,
			'mel_low_freq': 20,
			'cepstral_lifter': 22.0,
			'dither': 0.0,
			'window_type': 'povey',
			'use_energy': False,
			'energy_floor': 0.0,
			'raw_energy': True,
			'preemphasis_coefficient': 0.97,
			'model_version': 1
		}

		path = Path(self.Commons.rootDir(), 'trained/hotwords/snips_hotword', self.wakeword.username.lower())

		if path.exists():
			self.logWarning('Destination directory for new wakeword already exists, deleting')
			shutil.rmtree(path)

		path.mkdir()

		(path/'config.json').write_text(json.dumps(config, indent='\t'))

		for i in range(1, 4):
			shutil.move(Path(tempfile.gettempdir(), f'{i}.wav'), path/f'{i}.wav')

		self.ThreadManager.newThread(name='SatelliteWakewordUpload', target=self._upload, args=[path, self._wakeword.username], autostart=True)

		self._state = WakewordRecorderState.IDLE


	def uploadToNewDevice(self, uid: str):
		directory = Path(self.Commons.rootDir(), 'trained/hotwords/snips_hotword')
		for fiile in directory.iterdir():
			if (directory/fiile).is_file():
				continue

			self._upload(directory/fiile, uid)


	def _upload(self, path: Path, uid: str = ''):
		wakewordName, zipPath = self._prepareHotword(path)

		for device in self.DeviceManager.getDevicesByType(deviceType=self.DeviceManager.SAT_TYPE, connectedOnly=False):
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
