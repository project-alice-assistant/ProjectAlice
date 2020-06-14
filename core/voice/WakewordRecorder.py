import json
from pathlib import Path
from typing import Optional

import paho.mqtt.client as mqtt
import re
import shutil
import struct
import tempfile
from enum import Enum
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
		for i in range(1, 4):
			file = Path(f'/tmp/{i}_raw.wav')
			if file.exists():
				file.unlink()

		self._wakeword = Wakeword(username)


	def addASample(self):
		self.wakeword.newSample()
		self.state = WakewordRecorderState.RECORDING


	def onAudioFrame(self, message: mqtt.MQTTMessage, siteId: str):
		if self.state != WakewordRecorderState.RECORDING:
			return

		# @author DasBasti
		# https://gist.github.com/DasBasti/050bf6c3232d4bb54c741a1f057459d3

		try:
			riff, size, fformat = struct.unpack('<4sI4s', message.payload[:12])

			if riff != b'RIFF':
				self.logError('Wakeword capture frame parse error')
				return

			if fformat != b'WAVE':
				self.logError('Wakeword capture frame wrong format')
				return

			chunkHeader = message.payload[12:20]
			subChunkId, subChunkSize = struct.unpack('<4sI', chunkHeader)

			samplerate = self.AudioServer.SAMPLERATE
			channels = 2
			if subChunkId == b'fmt ':
				aFormat, channels, samplerate, byterate, blockAlign, bps = struct.unpack('HHIIHH', message.payload[20:36])

			record = self.wakeword.getSample()

			# noinspection PyProtectedMember
			if not record._datawritten:
				record.setframerate(samplerate)
				record.setnchannels(channels)
				record.setsampwidth(2)

			chunkOffset = 52
			while chunkOffset < size:
				subChunk2Id, subChunk2Size = struct.unpack('<4sI', message.payload[chunkOffset:chunkOffset + 8])
				chunkOffset += 8
				if subChunk2Id == b'data' and self._state == WakewordRecorderState.RECORDING:
					record.writeframes(message.payload[chunkOffset:chunkOffset + subChunk2Size])

				chunkOffset = chunkOffset + subChunk2Size + 8

		except Exception as e:
			self.logError(f'Error capturing wakeword: {e}')


	def _workAudioFile(self):
		sample = self.wakeword.getSample()

		# noinspection PyProtectedMember
		if not sample._datawritten:
			self.logError('Something went wrong capturing audio, no data available in sample')
			self._state = WakewordRecorderState.IDLE
			return

		sample.close()

		self._state = WakewordRecorderState.TRIMMING

		self.wakeword.getSample().close()

		filepath = self.wakeword.getSamplePath()
		if not filepath.exists():
			self.logError(f'Raw wakeword **{len(self.wakeword.samples)}** wasn\'t found')
			self._state = WakewordRecorderState.IDLE
			return


		sound = AudioSegment.from_file(filepath, format='wav', frame_rate=self._sampleRate)
		startTrim = self.detectLeadingSilence(sound)
		endTrim = self.detectLeadingSilence(sound.reverse())
		duration = len(sound)
		trimmed = sound[startTrim: duration - endTrim]
		reworked = trimmed.set_frame_rate(self.AudioServer.SAMPLERATE)
		reworked = reworked.set_channels(1)

		reworked.export(Path(tempfile.gettempdir(), f'{len(self.wakeword.samples)}.wav'), format='wav')
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

		(path/'config.json').write_text(json.dumps(config, indent=4))

		for i in range(1, 4):
			shutil.move(Path(tempfile.gettempdir(), f'{i}.wav'), path/f'{i}.wav')

		self._addWakewordToSnips(path)
		self.ThreadManager.newThread(name='SatelliteWakewordUpload', target=self._upload, args=[path, self._wakeword.username], autostart=True)

		self._state = WakewordRecorderState.IDLE


	def _addWakewordToSnips(self, path: Path):
		models: list = self.ConfigManager.getSnipsConfiguration('snips-hotword', 'model', createIfNotExist=True)

		if not isinstance(models, list):
			models = list()

		wakewordName = path.name

		addHeySnips = True
		copy = models.copy()
		for i, model in enumerate(copy):
			if wakewordName in model:
				del models[i]
			elif '/snips_hotword=' in model:
				addHeySnips = False

		if addHeySnips:
			models.append(str(Path(self.Commons.rootDir(), 'trained/hotwords/snips_hotword/hey_snips=0.53')))

		models.append(f'{path}=0.52')
		self.ConfigManager.updateSnipsConfiguration('snips-hotword', 'model', models, restartSnips=True)


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

			port = 8080 + len(self._wakewordUploadThreads)

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
		wakewords = self.ConfigManager.getSnipsConfiguration(parent='snips-hotword', key='model', createIfNotExist=False)

		usernameMatch = re.compile(f'.*/{username}=[0-9.]+$')
		for wakeword in wakewords:
			match = re.search(usernameMatch, wakeword)
			if match:
				return wakeword
		return None


	def getUserWakewordSensitivity(self, username: str) -> Optional[float]:
		wakeword = self.getUserWakeword(username)
		if wakeword is None:
			return None

		sensitivity = re.findall('[0-9.]+$', wakeword)
		return round(float(sensitivity[0]), 2) if sensitivity else None


	def setUserWakewordSensitivity(self, username: str, sensitivity: float) -> bool:
		wakewords = self.ConfigManager.getSnipsConfiguration(parent='snips-hotword', key='model', createIfNotExist=False)
		rebuild = list()

		if sensitivity > 1:
			sensitivity = 1
		elif sensitivity < 0:
			sensitivity = 0

		usernameMatch = re.compile(f'.*/{username}=[0-9.]+$')
		sensitivitySub = re.compile('=[0-9.]+$')
		update = False
		for wakeword in wakewords:
			match = re.search(usernameMatch, wakeword)
			if not match:
				rebuild.append(wakeword)
				continue

			update = True
			updated = re.sub(sensitivitySub, f'={round(float(sensitivity), 2)}', wakeword)
			rebuild.append(updated)

		if update:
			self.ConfigManager.updateSnipsConfiguration(parent='snips-hotword', key='model', value=rebuild, restartSnips=False, createIfNotExist=False)
			self.WakewordManager.restartEngine()

		return update


	@property
	def state(self) -> WakewordRecorderState:
		return self._state


	@state.setter
	def state(self, value: WakewordRecorderState):
		self._state = value


	@property
	def wakeword(self) -> Wakeword:
		return self._wakeword
