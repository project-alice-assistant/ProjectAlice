"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>

    authors: 	            Psycho <https://github.com/Psychokiller1888>

	retired or
	inactive authors:       Jierka <https://github.com/jr-k>
							maxbachmann <https://github.com/maxbachmann>
"""
import logging.handlers
import signal
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import os
import psutil

from core.Initializer import Initializer
from core.util.model import BashFormatting, HtmlFormatting
from core.util.model.MqttLoggingHandler import MqttLoggingHandler

_logger = logging.getLogger('ProjectAlice')
_logger.setLevel(logging.INFO)

logFileFormatter = logging.Formatter('%(asctime)s [%(threadName)s] - [%(levelname)s] - %(message)s')
bashFormatter = BashFormatting.Formatter()
htmlFormatter = HtmlFormatting.Formatter()

date = int(datetime.now().strftime('%Y%m%d'))
logsMountpoint = Path(Path(__file__).resolve().parent, 'var', 'logs')

logFileHandler = logging.FileHandler(filename=f'{logsMountpoint}/logs.log', mode='w')
rotatingHandler = logging.handlers.RotatingFileHandler(filename=f'{logsMountpoint}/{date}-logs.log', mode='a', maxBytes=100000, backupCount=20)
streamHandler = logging.StreamHandler()
mqttHandler = MqttLoggingHandler()

logFileHandler.setFormatter(logFileFormatter)
rotatingHandler.setFormatter(logFileFormatter)
mqttHandler.setFormatter(htmlFormatter)
streamHandler.setFormatter(bashFormatter)

_logger.addHandler(logFileHandler)
_logger.addHandler(rotatingHandler)
_logger.addHandler(streamHandler)
_logger.addHandler(mqttHandler)


def exceptionListener(*exc_info):
	global _logger
	_logger.error('An unhandled exception occured')
	text = ''.join(traceback.format_exception(*exc_info))
	_logger.error(f'- Traceback: {text}')


sys.excepthook = exceptionListener

from core.ProjectAlice import ProjectAlice
import subprocess


# noinspection PyUnusedLocal
def stopHandler(signum, frame):
	global RUNNING
	RUNNING = False


def restart():
	global RUNNING
	RUNNING = False


def main():
	subprocess.run(['clear'])
	global RUNNING
	RUNNING = True

	signal.signal(signal.SIGINT, stopHandler)
	signal.signal(signal.SIGTERM, stopHandler)

	Initializer().initProjectAlice()
	projectAlice = ProjectAlice(restartHandler=restart)
	try:
		while RUNNING:
			time.sleep(0.1)
	except KeyboardInterrupt:
		_logger.info('Interruption detected')
	finally:
		projectAlice.onStop()
		_logger.info('Project Alice stopped, see you soon!')
		if projectAlice.restart:
			time.sleep(3)
			sys.stdout.flush()
			try:
				# Close everything related to ProjectAlice, allows restart without component failing
				p = psutil.Process(os.getpid())
				for h in p.open_files() + p.connections():
					os.close(h.fd)
			except Exception as e:
				_logger.error(f'Failed restarting ProjectAlice: {e}')

			python = sys.executable
			os.execl(python, python, *sys.argv)


RUNNING = False
if __name__ == '__main__':
	main()
