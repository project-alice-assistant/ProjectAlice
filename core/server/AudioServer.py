import io
import wave

import pyaudio

from core.base.model.Manager import Manager
from core.commons import constants


class AudioManager(Manager):

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

					frame = wav.readframes(256)
					while frame:
						audioStream.write(frame)
						frame = wav.readframes(256)

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
