# -*- coding: utf-8 -*-
import json
import wave

import os
import pyaudio
import shutil
import tempfile
from enum import Enum
from pydub import AudioSegment

import core.base.Managers as managers
from core.base.Manager import Manager
from core.commons import commons
from core.commons.commons import shutUpAlsaFFS
from core.voice.model.Wakeword import Wakeword
from core.voice.model.WakewordUploadThread import WakewordUploadThread


class WakewordManagerState(Enum):
	IDLE = 1
	RECORDING = 2
	VALIDATING = 3
	CONFIRMING = 4
	TRIMMING = 5
	FINALIZING = 6


class WakewordManager(Manager):
	NAME = 'WakewordManager'

	RECORD_SECONDS = 2.5
	THRESHOLD = -45.0


	def __init__(self, mainClass):
		super().__init__(mainClass, self.NAME)
		managers.WakewordManager = self

		self._state = WakewordManagerState.IDLE

		self._audio = None
		self._wakeword = None
		self._threshold = 0
		self._wakewordUploadThreads = list()


	def onStart(self):
		super().onStart()
		self._threshold = self.THRESHOLD


	def onStop(self):
		super().onStop()

		for thread in self._wakewordUploadThreads:
			if thread.isAlive():
				thread.join(timeout=2)


	@property
	def wakeword(self) -> Wakeword:
		return self._wakeword


	@property
	def state(self) -> WakewordManagerState:
		return self._state


	@state.setter
	def state(self, value: WakewordManagerState):
		self._state = value


	def isDefaultThreshold(self) -> bool:
		return self._threshold == self.THRESHOLD


	def newWakeword(self, username: str):
		for i in range(1, 4):
			file = os.path.join('/tmp', '{}_raw.wav'.format(i))
			if os.path.isfile(file):
				os.remove(path=file)

		self._wakeword = Wakeword(username)


	def addASample(self):
		self._state = WakewordManagerState.RECORDING
		number = len(self._wakeword.samples) + 1
		managers.ThreadManager.newThread(name = 'captureWakeword', target = self._captureWakeword, args = [number], autostart = True)


	def _captureWakeword(self, number: int):
		with shutUpAlsaFFS():
			self._audio = pyaudio.PyAudio()

		stream = self._audio.open(
			format = self._audio.get_format_from_width(2),
			channels = managers.ConfigManager.getAliceConfigByName('micChannels'),
			rate = managers.ConfigManager.getAliceConfigByName('micSampleRate'),
			input = True,
			frames_per_buffer = int(managers.ConfigManager.getAliceConfigByName('micSampleRate') / 10)
		)
		self._logger.info('[{}] Now recording...'.format(self.name))
		frames = list()

		for i in range(0, int(managers.ConfigManager.getAliceConfigByName('micSampleRate') / int(managers.ConfigManager.getAliceConfigByName('micSampleRate') / 10) * self.RECORD_SECONDS)):
			data = stream.read(int(managers.ConfigManager.getAliceConfigByName('micSampleRate') / 10))
			frames.append(data)

		self._logger.info('[{}] Recording over'.format(self.name))
		stream.stop_stream()
		stream.close()
		self._audio.terminate()

		wav = wave.open(os.path.join(tempfile.gettempdir(), '{}_raw.wav'.format(number)), 'w')
		wav.setnchannels(managers.ConfigManager.getAliceConfigByName('micChannels'))
		wav.setsampwidth(2)
		wav.setframerate(managers.ConfigManager.getAliceConfigByName('micSampleRate'))
		wav.writeframes((b''.join(frames)))
		wav.close()

		self._wakeword.samples.append(wav)
		self._workAudioFile(number)


	def _workAudioFile(self, number: int):
		self._state = WakewordManagerState.TRIMMING
		sound = AudioSegment.from_file(os.path.join(tempfile.gettempdir(), '{}_raw.wav'.format(number)), format='wav', frame_rate=managers.ConfigManager.getAliceConfigByName('micSampleRate'))
		startTrim = self.detectLeadingSilence(sound)
		endTrim = self.detectLeadingSilence(sound.reverse())
		duration = len(sound)
		trimmed = sound[startTrim : duration - endTrim]
		reworked = trimmed.set_frame_rate(16000)
		reworked = reworked.set_channels(1)

		reworked.export(os.path.join(tempfile.gettempdir(), '{}.wav'.format(number)), format='wav')
		self._state = WakewordManagerState.CONFIRMING


	def trimMore(self):
		self._threshold += 2
		self._workAudioFile(len(self._wakeword.samples))


	def trimLess(self):
		self._threshold -= 2
		self._workAudioFile(len(self._wakeword.samples))


	def detectLeadingSilence(self, sound):
		trim = 0
		while sound[trim : trim + 10].dBFS < self._threshold and trim < len(sound):
			trim += 10
		return trim


	def getLastSampleNumber(self) -> int:
		if self._wakeword and self._wakeword.samples:
			return len(self._wakeword.samples)
		else:
			return 1


	def finalizeWakeword(self):
		self._logger.info('[{}] Finalyzing wakeword'.format(self.name))
		self._state = WakewordManagerState.FINALIZING

		config = {
			'hotword_key'            : self._wakeword.username.lower(),
			'kind'                   : 'personal',
			'dtw_ref'                : 0.22,
			'from_mfcc'              : 1,
			'to_mfcc'                : 13,
			'band_radius'            : 10,
			'shift'                  : 10,
			'window_size'            : 10,
			'sample_rate'            : 16000,
			'frame_length_ms'        : 25.0,
			'frame_shift_ms'         : 10.0,
			'num_mfcc'               : 13,
			'num_mel_bins'           : 13,
			'mel_low_freq'           : 20,
			'cepstral_lifter'        : 22.0,
			'dither'                 : 0.0,
			'window_type'            : 'povey',
			'use_energy'             : False,
			'energy_floor'           : 0.0,
			'raw_energy'             : True,
			'preemphasis_coefficient': 0.97,
			'model_version'          : 1
		}

		path = os.path.join(commons.rootDir(), 'trained', 'hotwords', self.wakeword.username.lower())

		if os.path.isdir(path):
			self._logger.warning('[{}] Destination directory for new wakeword already exists, deleting'.format(self.name))
			shutil.rmtree(path)

		os.mkdir(path)

		with open(os.path.join(path, 'config.json'), 'w') as file:
			json.dump(config, file, indent=4)

		for i in range(1, 4):
			shutil.move(os.path.join(tempfile.gettempdir(), '{}.wav'.format(i)), os.path.join(path, '{}.wav'.format(i)))

		self._addWakewordToSnips(path)
		managers.ThreadManager.newThread(name='SatelliteWakewordUpload', target=self._upload, args=[path, self._wakeword.username], autostart=True)

		self._state = WakewordManagerState.IDLE


	def _addWakewordToSnips(self, path: str):
		# TODO unhardcode sensitivity
		models: list = managers.ConfigManager.getSnipsConfiguration('snips-hotword', 'model', createIfNotExist=True)

		if not isinstance(models, list):
			models = list()

		wakewordName = os.path.split(path)[-1]

		add = True
		copy = models.copy()
		for i, model in enumerate(copy):
			if wakewordName in model:
				models.pop(i)
			elif '/snips_hotword=' in model:
				add = False

		if add:
			models.append(os.path.join(commons.rootDir(), 'trained', 'hotwords', 'snips_hotword=0.53'))

		models.append('{}=0.52'.format(path))
		managers.ConfigManager.updateSnipsConfiguration('snips-hotword', 'model', models, restartSnips=True)

		self._upload(path)


	def uploadToNewDevice(self, uid: str):
		d = os.path.join(commons.rootDir(), 'trained', 'hotwords')
		for f in os.listdir(d):
			if os.path.isfile(os.path.join(d, f)):
				continue

			self._upload(os.path.join(d, f), uid)


	def _upload(self, path: str, uid: str = ''):
		wakewordName, zipPath = self._prepareHotword(path)

		l = len(managers.DeviceManager.getDevicesByType(deviceType='AliceSatellite', connectedOnly=False)) if uid else 1
		for _ in range(0, l):
			port = 8080 + len(self._wakewordUploadThreads)

			payload = {
				'ip': commons.getLocalIp(),
				'port': port,
				'name': wakewordName
			}

			if uid:
				payload['uid'] = uid

			managers.MqttServer.publish(topic='projectalice/devices/alice/newhotword', payload=payload)
			thread = WakewordUploadThread(host=commons.getLocalIp(), zipPath=zipPath, port=port)
			self._wakewordUploadThreads.append(thread)
			thread.start()


	def _prepareHotword(self, path: str) -> tuple:
		wakewordName = os.path.split(path)[-1]
		zipPath = os.path.join(path, '..', wakewordName + '.zip')

		self._logger.info('[{}] Cleaning up {}'.format(self.name, wakewordName))
		if os.path.isfile(zipPath):
			os.remove(zipPath)

		self._logger.info('[{}] Packing wakeword {}'.format(self.name, wakewordName))
		shutil.make_archive(base_name=os.path.splitext(zipPath)[0], format='zip', root_dir=path)

		return wakewordName, zipPath
