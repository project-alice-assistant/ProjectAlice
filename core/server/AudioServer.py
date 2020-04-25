import wave
from pathlib import Path

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
			self._isActive = False
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
		self._sample = None


	def onStart(self):
		super().onStart()
		self.MqttManager.mqttClient.subscribe(constants.TOPIC_AUDIO_FRAME.format(constants.DEFAULT_SITE_ID))
		self.ThreadManager.newThread(name='audioPublisher', target=self.publishAudio)


	def onStop(self):
		super().onStop()
		self.MqttManager.mqttClient.unsubscribe(constants.TOPIC_AUDIO_FRAME.format(constants.DEFAULT_SITE_ID))


	def onHotword(self, siteId: str, user: str = constants.UNKNOWN_USER):
		if not self._sample:
			sample = Path('sample.wav')
			if sample.exists():
				sample.unlink()

			self._sample = wave.open('sample.wav', 'wb')
			self._sample.setsampwidth(2)
			self._sample.setframerate(self.ConfigManager.getAliceConfigByName('micSampleRate'))
			self._sample.setnchannels(self.ConfigManager.getAliceConfigByName('micChannels'))

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


	def publishAudioFrames(self, frames: bytes):
		with io.BytesIO() as buffer:
			with wave.open(buffer, 'wb') as wav:
				wav.setnchannels(1)
				wav.setsampwidth(2)
				wav.setframerate(16000)
				wav.writeframes(frames)

			audioFrames = buffer.getvalue()
			self.MqttManager.publish(topic=constants.TOPIC_AUDIO_FRAME.format(constants.DEFAULT_SITE_ID), payload=audioFrames)


	def onAudioFrame(self, message, siteId: str):
		if self._sample:
			with io.BytesIO(message.payload) as buffer:
				try:
					with wave.open(buffer, 'rb') as wav:
						frame = wav.readframes(512)
						while frame:
							self._sample.writeframes(frame)
							frame = wav.readframes(512)

				except Exception as e:
					self.logError(f'Playing wav failed with error: {e}')


	def onCaptured(self, session):
		self._sample.close()
		self._sample = None


	def onSessionTimeout(self, session):
		self._sample.close()
		self._sample = None


	def onPlayBytes(self, requestId: str, siteId: str, payload: bytes):
		if siteId != constants.DEFAULT_SITE_ID:
			return

		with io.BytesIO(payload) as buffer:
			try:
				with wave.open(buffer, 'rb') as wav:
					sampleWidth = wav.getsampwidth()
					nFormat = self._audio.get_format_from_width(sampleWidth)
					channels = wav.getnchannels()
					framerate = wav.getframerate()

					audioStream = self._audio.open(
						format=nFormat,
						channels=channels,
						rate=framerate,
						output=True
					)

					self.logDebug(f'Playing wav stream using **{self._audioOutput["name"]}** on site id **{siteId}**')

					frame = wav.readframes(512)
					while frame:
						audioStream.write(frame)
						frame = wav.readframes(512)

					audioStream.stop_stream()
					audioStream.close()

			except Exception as e:
				self.logError(f'Playing wav failed with error: {e}')

		self.MqttManager.publish(
			topic=constants.TOPIC_PLAY_BYTES_FINISHED.format(siteId),
			payload={
				'id': requestId
			}
		)
