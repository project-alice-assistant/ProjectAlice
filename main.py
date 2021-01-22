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
                            philipp2310 <https://github.com/philipp2310>

	retired or
	inactive authors:       Jierka <https://github.com/jr-k>
							maxbachmann <https://github.com/maxbachmann>
"""

import subprocess

subprocess.run(['clear'])

try:
	from pathlib import Path
	import json

	conf = json.loads(Path('debug_server.json').read_text())
	if not conf['enable']:
		raise Exception

	import pydevd_pycharm

	pydevd_pycharm.settrace(conf['server'], port=conf['port'], stdoutToServer=conf['stdout'], stderrToServer=conf['stderr'])
except:
	# Do nothing, this is only for debug server, advanced stuff
	pass

import logging.handlers
from datetime import datetime
from core.util.model import FileFormatting, BashFormatting

_logger = logging.getLogger('ProjectAlice')
_logger.setLevel(logging.INFO)

date = int(datetime.now().strftime('%Y%m%d'))
logsMountpoint = Path(Path(__file__).resolve().parent, 'var', 'logs')

logFileHandler = logging.FileHandler(filename=f'{logsMountpoint}/logs.log', mode='w')
rotatingHandler = logging.handlers.RotatingFileHandler(filename=f'{logsMountpoint}/{date}-logs.log', mode='a', maxBytes=100000, backupCount=20)
streamHandler = logging.StreamHandler()

logFileFormatter = FileFormatting.Formatter()
bashFormatter = BashFormatting.Formatter()
logFileHandler.setFormatter(logFileFormatter)
rotatingHandler.setFormatter(logFileFormatter)
streamHandler.setFormatter(bashFormatter)

_logger.addHandler(logFileHandler)
_logger.addHandler(rotatingHandler)
_logger.addHandler(streamHandler)

from core.Initializer import Initializer

Initializer().initProjectAlice()

import signal
import sys
import time
import traceback

# This needs access to non native python packages, cannot init before the initializer is done
from core.util.model import HtmlFormatting
from core.util.model.MqttLoggingHandler import MqttLoggingHandler

htmlFormatter = HtmlFormatting.Formatter()
mqttHandler = MqttLoggingHandler()
#mqttHandler.setFormatter(htmlFormatter)
_logger.addHandler(mqttHandler)


def exceptionListener(*exc_info):  # NOSONAR
	global _logger
	_logger.error('[Project Alice]           An unhandled exception occured')
	text = ''.join(traceback.format_exception(*exc_info))
	_logger.error(f'- Traceback: {text}')


sys.excepthook = exceptionListener

from core.ProjectAlice import ProjectAlice


# noinspection PyUnusedLocal
def stopHandler(signum, frame):
	global RUNNING
	RUNNING = False


def restart():
	global RUNNING
	RUNNING = False


def main():
	global RUNNING
	RUNNING = True

	signal.signal(signal.SIGINT, stopHandler)
	signal.signal(signal.SIGTERM, stopHandler)

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
