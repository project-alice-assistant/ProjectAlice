import socket
from pathlib import Path
from socket import timeout
from threading import Thread

from core.util.model.Logger import Logger


class WakewordUploadThread(Thread):

	def __init__(self, host: str, port: int, zipPath: str):
		super().__init__()
		self._logger = Logger()

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
				self._logger.logInfo(f'New device connected: {addr}')

				with self._zipPath.open(mode='rb') as f:
					data = f.read(1024)
					while data:
						conn.send(data)
						data = f.read(1024)

				self._logger.logInfo(f'Waiting on a feedback from {addr[0]}')
				conn.settimeout(20)
				try:
					while True:
						answer = conn.recv(1024).decode()
						if not answer:
							self._logger.logInfo('The device closed the connection before confirming...')
							break

						if answer == '0':
							self._logger.logInfo(f'Wakeword "{wakewordName}" upload to {addr[0]} success')
							break
						elif answer == '-1':
							self._logger.logWarning('The device failed downloading the hotword')
							break
						elif answer == '-2':
							self._logger.logWarning('The device failed installing the hotword')
							break
				except timeout:
					self._logger.logWarning('The device did not confirm the operation as successfull in time. The hotword installation might have failed')
		except Exception as e:
			self._logger.logInfo(f'Error uploading wakeword: {e}')
