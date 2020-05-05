import time
import wave

import io
import pyaudio
from webrtcvad import Vad

from core.base.model.Manager import Manager
from core.commons import constants


class AudioManager(Manager):

	# Inspired by https://github.com/koenvervloesem/hermes-audio-server

	def __init__(self):
		super().__init__()

		if self.ConfigManager.getAliceConfigByName('disableSoundAndMic'):
			return

		with self.Commons.shutUpAlsaFFS():
			self._audio = pyaudio.PyAudio()

		try:
			self._audioOutput = self._audio.get_default_output_device_info()
		except:
			self.logFatal('Audio output not found, cannot continue')
			return

		self.logInfo(f'Using **{self._audioOutput["name"]}** for audio output')

		try:
			self._audioInput = self._audio.get_default_input_device_info()
		except:
			self.logFatal('Audio input not found, cannot continue')
			return

		self.logInfo(f'Using **{self._audioInput["name"]}** for audio input')
		self._vad = Vad(2)


	def onStart(self):
		super().onStart()
		self.MqttManager.mqttClient.subscribe(constants.TOPIC_AUDIO_FRAME.format(constants.DEFAULT_SITE_ID))

		if not self.ConfigManager.getAliceConfigByName('disableSoundAndMic'):
			self.ThreadManager.newThread(name='audioPublisher', target=self.publishAudio)


	def onStop(self):
		super().onStop()
		self.MqttManager.mqttClient.unsubscribe(constants.TOPIC_AUDIO_FRAME.format(constants.DEFAULT_SITE_ID))

		if not self.ConfigManager.getAliceConfigByName('disableSoundAndMic'):
			self._audio.terminate()


	def onHotword(self, siteId: str, user: str = constants.UNKNOWN_USER):
		self.MqttManager.publish(
			topic=constants.TOPIC_ASR_TOGGLE_ON,
			payload={
				'siteId': siteId
			}
		)


	def publishAudio(self):
		self.logInfo('Starting audio publisher')
		audioStream = self._audio.open(
			format=pyaudio.paInt16,
			channels=1,
			rate=self.ConfigManager.getAliceConfigByName('micSampleRate'),
			frames_per_buffer=320,
			input=True
		)

		speech = False
		silence = 16000 / 320
		speechFrames = 0
		minSpeechFrames = round(silence / 3)

		while True:
			if self.ProjectAlice.shuttingDown:
				break

			try:
				frames = audioStream.read(num_frames=320, exception_on_overflow=False)
				if self._vad.is_speech(frames, 16000):
					if not speech and speechFrames < minSpeechFrames:
						speechFrames += 1
					elif speechFrames >= minSpeechFrames:
						speech = True
						self.MqttManager.publish(
							topic=constants.TOPIC_VAD_UP.format(constants.DEFAULT_SITE_ID),
							payload={
								'siteId': constants.DEFAULT_SITE_ID
							})
						silence = 16000 / 320
						speechFrames = 0
				else:
					if speech:
						if silence > 0:
							silence -= 1
						else:
							speech = False
							self.MqttManager.publish(
								topic=constants.TOPIC_VAD_DOWN.format(constants.DEFAULT_SITE_ID),
								payload={
									'siteId': constants.DEFAULT_SITE_ID
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
				wav.setframerate(16000)
				wav.writeframes(frames)

			audioFrames = buffer.getvalue()
			self.MqttManager.publish(topic=constants.TOPIC_AUDIO_FRAME.format(constants.DEFAULT_SITE_ID), payload=bytearray(audioFrames))


	def onPlayBytes(self, requestId: str, payload: bytearray, siteId: str, sessionId: str = None):
		if siteId != constants.DEFAULT_SITE_ID or self.ConfigManager.getAliceConfigByName('disableSoundAndMic'):
			return

		with io.BytesIO(payload) as buffer:
			try:
				with wave.open(buffer, 'rb') as wav:
					sampleWidth = wav.getsampwidth()
					nFormat = self._audio.get_format_from_width(sampleWidth)
					channels = wav.getnchannels()
					framerate = wav.getframerate()

					def streamCallback(_inData, frameCount, _timeInfo, _status) -> tuple:
						data = wav.readframes(frameCount)
						return data, pyaudio.paContinue

					audioStream = self._audio.open(
						format=nFormat,
						channels=channels,
						rate=framerate,
						output=True,
						stream_callback=streamCallback
					)

					self.logDebug(f'Playing wav stream using **{self._audioOutput["name"]}** on site id **{siteId}**')
					audioStream.start_stream()
					while audioStream.is_active():
						time.sleep(0.1)

					audioStream.stop_stream()
					audioStream.close()
			except Exception as e:
				self.logError(f'Playing wav failed with error: {e}')

		# Session id support is not Hermes protocol official
		self.MqttManager.publish(
			topic=constants.TOPIC_PLAY_BYTES_FINISHED.format(siteId),
			payload={
				'id': requestId,
				'sessionId': sessionId
			}
		)
