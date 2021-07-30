#  Copyright (c) 2021
#
#  This file, Recorder.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.07.30 at 19:56:37 CEST

#  Copyright (c) 2021
#
#  This file, Recorder.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:45 CEST

import io
import paho.mqtt.client as mqtt
import queue
import wave
from typing import Optional

from core.base.model.ProjectAliceObject import ProjectAliceObject
from core.dialog.model.DialogSession import DialogSession
from core.util.model.AliceEvent import AliceEvent
from core.voice.WakewordRecorder import WakewordRecorderState


class Recorder(ProjectAliceObject):

	def __init__(self, timeoutFlag: AliceEvent, user: str, deviceUid: str):
		super().__init__()
		self._user = user,
		self._deviceUid = deviceUid
		self._recording = False
		self._timeoutFlag = timeoutFlag
		self._buffer = queue.Queue()


	def __enter__(self):
		self.startRecording()
		return self


	def __exit__(self, excType, excVal, excTb):
		self.stopRecording()


	@property
	def isRecording(self) -> bool:
		return self._recording


	def onSessionError(self, session: DialogSession):
		self.stopRecording()


	def startRecording(self):
		self._recording = True


	def stopRecording(self):
		self._recording = False
		self._buffer.put(None)


	def onAudioFrame(self, message: mqtt.MQTTMessage, deviceUid: str):
		with io.BytesIO(message.payload) as buffer:
			try:
				with wave.open(buffer, 'rb') as wav:
					frame = wav.readframes(512)
					while frame:
						self._buffer.put(frame)

						if self.ConfigManager.getAliceConfigByName('recordAudioAfterWakeword') or self.WakewordRecorder.state == WakewordRecorderState.RECORDING:
							self.AudioServer.recordFrame(deviceUid, frame)

						frame = wav.readframes(512)

			except Exception as e:
				self.logError(f'Error recording user speech: {e}')


	def __iter__(self):
		while self._recording:
			if self._timeoutFlag.is_set():
				return

			chunk = self._buffer.get()

			if not chunk:
				break

			yield chunk

		# Empty the buffer
		data = list()
		while not self._buffer.empty():
			chunk = self._buffer.get(block=False)
			if not chunk or not self._recording:
				break

			data.append(chunk)

		yield b''.join(data)


	def audioStream(self) -> Optional[bytes]:
		while not self._buffer.empty() or self._recording:
			if self._timeoutFlag.is_set():
				return

			chunk = self._buffer.get()
			if not chunk:
				return

			data = [chunk]

			while self._recording:
				try:
					chunk = self._buffer.get(block=False)
					if not chunk or not self._recording:
						return

					data.append(chunk)
				except queue.Empty:
					break

			yield b''.join(data)
