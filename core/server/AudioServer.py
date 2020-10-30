import io
import time
import wave
from pathlib import Path
from typing import Dict, Optional

import sounddevice as sd
from webrtcvad import Vad

from core.ProjectAliceExceptions import PlayBytesStopped
from core.base.model.Manager import Manager
from core.commons import constants
from core.dialog.model.DialogSession import DialogSession
from core.util.model.AliceEvent import AliceEvent


class AudioManager(Manager):

	SAMPLERATE = 16000
	FRAMES_PER_BUFFER = 320

	LAST_USER_SPEECH = 'var/cache/lastUserpeech_{}_{}.wav'
	SECOND_LAST_USER_SPEECH = 'var/cache/secondLastUserSpeech_{}_{}.wav'

	def __init__(self):
		super().__init__()

		self._stopPlayingFlag: Optional[AliceEvent] = None
		self._playing = False
		self._waves: Dict[str, wave.Wave_write] = dict()
		self._audioInputStream = None

		if self.ConfigManager.getAliceConfigByName('disableSoundAndMic'):
			return

		self._vad = Vad(2)

		devices = sd.query_devices()

		for device in devices:
			print(device)

		print(devices)

		try:
			self._audioOutput = sd.query_devices()[0]
		except:
			self.logFatal('Audio output not found, cannot continue')
			return
		else:
			self.logInfo(f'Using **{self._audioOutput["name"]}** for audio output')

		try:
			self._audioInput = sd.query_devices()[0]
		except:
			self.logFatal('Audio input not found, cannot continue')
		else:
			self.logInfo(f'Using **{self._audioInput["name"]}** for audio input')


	def onStart(self):
		super().onStart()
		self._stopPlayingFlag = self.ThreadManager.newEvent('stopPlaying')
		self.MqttManager.mqttClient.subscribe(constants.TOPIC_AUDIO_FRAME.format(self.ConfigManager.getAliceConfigByName('uuid')))

		if not self.ConfigManager.getAliceConfigByName('disableSoundAndMic'):
			self.ThreadManager.newThread(name='audioPublisher', target=self.publishAudio)


	def onStop(self):
		super().onStop()
		self._audioInputStream.stop(ignore_errors=True)
		self._audioInputStream.close(ignore_errors=True)
		self.MqttManager.mqttClient.unsubscribe(constants.TOPIC_AUDIO_FRAME.format(self.ConfigManager.getAliceConfigByName('uuid')))


	def onStartListening(self, session: DialogSession):
		if not self.ConfigManager.getAliceConfigByName('recordAudioAfterWakeword'):
			return

		path = Path(self.LAST_USER_SPEECH.format(session.user, session.siteId))

		if path.exists():
			path.rename(Path(self.SECOND_LAST_USER_SPEECH.format(session.user, session.siteId)))

		waveFile = wave.open(str(path), 'wb')
		waveFile.setsampwidth(2)
		waveFile.setframerate(self.AudioServer.SAMPLERATE)
		waveFile.setnchannels(1)
		self._waves[session.siteId] = waveFile


	def onCaptured(self, session: DialogSession):
		wav = self._waves.pop(session.siteId, None)
		if not wav:
			return
		wav.close()


	def recordFrame(self, siteId: str, frame: bytes):
		if siteId not in self._waves:
			return

		self._waves[siteId].writeframes(frame)


	def publishAudio(self):
		self.logInfo('Starting audio publisher')
		self._audioInputStream = sd.RawInputStream(
			dtype='int16',
			channels=1,
			samplerate=self.SAMPLERATE,
			blocksize=self.FRAMES_PER_BUFFER,
		)
		self._audioInputStream.start()

		speech = False
		silence = self.SAMPLERATE / self.FRAMES_PER_BUFFER
		speechFrames = 0
		minSpeechFrames = round(silence / 3)

		while True:
			if self.ProjectAlice.shuttingDown:
				break

			try:
				frames = self._audioInputStream.read(frames=self.FRAMES_PER_BUFFER)[0]

				if self._vad.is_speech(frames, self.SAMPLERATE):
					if not speech and speechFrames < minSpeechFrames:
						speechFrames += 1
					elif speechFrames >= minSpeechFrames:
						speech = True
						self.MqttManager.publish(
							topic=constants.TOPIC_VAD_UP.format(self.ConfigManager.getAliceConfigByName('uuid')),
							payload={
								'siteId': self.ConfigManager.getAliceConfigByName('uuid')
							})
						silence = self.SAMPLERATE / self.FRAMES_PER_BUFFER
						speechFrames = 0
				else:
					if speech:
						if silence > 0:
							silence -= 1
						else:
							speech = False
							self.MqttManager.publish(
								topic=constants.TOPIC_VAD_DOWN.format(self.ConfigManager.getAliceConfigByName('uuid')),
								payload={
									'siteId': self.ConfigManager.getAliceConfigByName('uuid')
								})
					else:
						speechFrames = 0

				self.publishAudioFrames(frames)
			except Exception as e:
				self.logDebug(f'Error publishing frame: {e}')


	def publishAudioFrames(self, frames: bytes):
		with io.BytesIO() as buffer:
			with wave.open(buffer, 'wb') as wav:
				wav.setnchannels(1)
				wav.setsampwidth(2)
				wav.setframerate(self.SAMPLERATE)
				wav.writeframes(frames)

			audioFrames = buffer.getvalue()
			self.MqttManager.publish(topic=constants.TOPIC_AUDIO_FRAME.format(self.ConfigManager.getAliceConfigByName('uuid')), payload=bytearray(audioFrames))


	def onPlayBytes(self, requestId: str, payload: bytearray, siteId: str, sessionId: str = None):
		if siteId != self.ConfigManager.getAliceConfigByName('uuid') or self.ConfigManager.getAliceConfigByName('disableSoundAndMic'):
			return

		self._playing = True
		with io.BytesIO(payload) as buffer:
			try:
				with wave.open(buffer, 'rb') as wav:
					channels = wav.getnchannels()
					framerate = wav.getframerate()

					def streamCallback(outdata, frameCount, _timeInfo, _status):
						try:
							data = wav.readframes(frameCount)
							outdata[:] = data
						except:
							raise PlayBytesStopped

					stream = sd.RawOutputStream(
						dtype='int16',
						channels=channels,
						samplerate=framerate,
						device=None,
						callback=streamCallback
					)

					self.logDebug(f'Playing wav stream using **{self._audioOutput["name"]}** audio output from site id **{self.DeviceManager.siteIdToDeviceName(siteId)}** (channels: {channels}, rate: {framerate})')
					stream.start()
					while stream.active:
						if self._stopPlayingFlag.is_set():
							stream.stop()
							stream.close()

							if sessionId:
								self.MqttManager.publish(
									topic=constants.TOPIC_TTS_FINISHED,
									payload={
										'id'       : requestId,
										'sessionId': sessionId,
										'siteId'   : siteId
									}
								)
								self.DialogManager.onEndSession(self.DialogManager.getSession(sessionId))

							raise PlayBytesStopped
						time.sleep(0.1)

					stream.stop()
					stream.close()
			except PlayBytesStopped:
				self.logDebug('Playing bytes stopped')
			except Exception as e:
				self.logError(f'Playing wav failed with error: {e}')
			finally:
				self._stopPlayingFlag.clear()
				self._playing = False

		# Session id support is not Hermes protocol official
		self.MqttManager.publish(
			topic=constants.TOPIC_PLAY_BYTES_FINISHED.format(siteId),
			payload={
				'id': requestId,
				'sessionId': sessionId
			}
		)


	def stopPlaying(self):
		self._stopPlayingFlag.set()


	@property
	def isPlaying(self) -> bool:
		return self._playing
