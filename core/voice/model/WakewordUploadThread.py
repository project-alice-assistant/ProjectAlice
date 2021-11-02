#  Copyright (c) 2021
#
#  This file, WakewordUploadThread.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:48 CEST

import socket
from pathlib import Path
from socket import timeout
from threading import Thread

from core.util.model.Logger import Logger


class WakewordUploadThread(Thread):

	def __init__(self, host: str, port: int, zipPath: str):
		super().__init__()
		self._logger = Logger(prepend='[HotwordUploadThread]')

		self.setDaemon(True)

		self._host = host
		self._port = port
		self._zipPath = Path(zipPath)


	def run(self):
		try:
			wakewordName = self._zipPath.stem

			with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
				sock.bind((self._host, self._port))
				self._logger.logInfo('Waiting for a device to connect')
				sock.listen()

				conn, addr = sock.accept()
				self._logger.logInfo(f'New device connected with address **{addr}**')

				with self._zipPath.open(mode='rb') as f:
					data = f.read(1024)
					while data:
						conn.send(data)
						data = f.read(1024)

				self._logger.logInfo(f'Waiting on a feedback from **{addr[0]}**')
				conn.settimeout(20)
				try:
					while True:
						answer = conn.recv(1024).decode()
						if not answer:
							raise Exception('The device closed the connection before confirming...')
						if answer == '0':
							self._logger.logInfo(f'Wakeword **{wakewordName}** upload to **{addr[0]}** success')
							break
						elif answer == '-1':
							raise Exception('The device failed downloading the hotword')
						elif answer == '-2':
							raise Exception('The device failed installing the hotword')
				except timeout:
					self._logger.logWarning('The device did not confirm the operation as successfull in time. The hotword installation might have failed')
		except Exception as e:
			self._logger.logError(f'Error uploading wakeword: {e}')
