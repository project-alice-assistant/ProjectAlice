# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/speech/microphone/transcribe_streaming_mic.py
"""

import pyaudio
from six.moves import queue

from core.base.SuperManager import SuperManager


class MicrophoneStream:
	"""Opens a recording stream as a generator yielding the audio chunks."""

	def __init__(self, rate, chunk):
		self._rate = rate
		self._chunk = chunk

		# Create a thread-safe buffer of audio data
		self._buff = queue.Queue()
		self.closed = True


	def __enter__(self):
		with SuperManager.getInstance().commons.shutUpAlsaFFS():
			self.audioInterface = pyaudio.PyAudio()

		self._audioStream = self.audioInterface.open(
			format=pyaudio.paInt16,
			# The API currently only supports 1-channel (mono) audio
			# https://goo.gl/z757pE
			channels=1, rate=self._rate,
			input=True, frames_per_buffer=self._chunk,
			# Run the audio stream asynchronously to fill the buffer object.
			# This is necessary so that the input device's buffer doesn't
			# overflow while the calling thread makes network requests, etc.
			stream_callback=self._fillBuffer,
		)

		self.closed = False

		return self


	def __exit__(self, typ, value, traceback):
		self._audioStream.stop_stream()
		self._audioStream.close()
		self.closed = True
		# Signal the generator to terminate so that the client's
		# streaming_recognize method will not block the process termination.
		self._buff.put(None)
		self.audioInterface.terminate()


	# noinspection PyUnusedLocal
	def _fillBuffer(self, in_data, frame_count, time_info, status_flags):
		"""Continuously collect data from the audio stream, into the buffer."""
		self._buff.put(in_data)
		return None, pyaudio.paContinue


	def generator(self):
		while not self.closed:
			# Use a blocking get() to ensure there's at least one chunk of
			# data, and stop iteration if the chunk is None, indicating the
			# end of the audio stream.
			chunk = self._buff.get()
			if not chunk:
				return
			data = [chunk]

			# Now consume whatever other data's still buffered.
			while True:
				try:
					chunk = self._buff.get(block=False)
					if not chunk:
						return
					data.append(chunk)
				except queue.Empty:
					break

			yield b''.join(data)
