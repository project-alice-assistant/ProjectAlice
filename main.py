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
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import os


def isVenv() -> bool:
	return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)


def restart():
	sys.stdout.flush()
	try:
		# Close everything related to ProjectAlice, allows restart without component failing
		process = psutil.Process(os.getpid())
		for handler in process.open_files() + process.connections():
			os.close(handler.fd)
	except Exception as e:
		print(f'Failed restarting Project Alice: {e}')

	python = sys.executable
	os.execl(python, python, *sys.argv)


PIP = './venv/bin/pip' if isVenv() else 'pip3'

result = subprocess.run(['dpkg-query', '-l', 'python3-pip'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if result.returncode:
	subprocess.run(['sudo', 'apt-get', 'install', '-y', 'python3-pip'])

try:
	import psutil
except:
	subprocess.run([PIP, 'install', 'psutil'])
	restart()

try:
	import requests
except:
	subprocess.run([PIP, 'install', 'requests'])
	restart()

try:
	import importlib_metadata
except:
	subprocess.run([PIP, 'install', 'importlib_metadata'])
	restart()

try:
	import yaml
except:
	subprocess.run([PIP, 'install', 'pyyaml'])
	restart()

from core.Initializer import Initializer
from core.util.model import BashFormatting, FileFormatting, HtmlFormatting
from core.util.model.MqttLoggingHandler import MqttLoggingHandler

_logger = logging.getLogger('ProjectAlice')
_logger.setLevel(logging.INFO)

logFileFormatter = FileFormatting.Formatter()
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


def exceptionListener(*exc_info): #NOSONAR
	global _logger
	_logger.error('[Project Alice]           An unhandled exception occured')
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
		_logger.info('[Project Alice]           Interruption detected, preparing shutdown')

	finally:
		if projectAlice.isBooted:
			projectAlice.onStop()

	_logger.info('[Project Alice]           Shutdown completed, see you soon!')
	if projectAlice.restart:
		time.sleep(3)
		restart()


RUNNING = False
if __name__ == '__main__':
	main()
