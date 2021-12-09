#  Copyright (c) 2021
#
#  This file, AliceWatchManager.py, is part of Project Alice.
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
#  Last modified: 2021.04.24 at 12:56:47 CEST
import json
import os
import subprocess
import traceback
from pathlib import Path

import requests

from core.base.model.Manager import Manager
from core.commons import constants


class BugReportManager(Manager):

	def __init__(self):
		super().__init__(name='BugReportManager')

		self._flagFile = Path('alice.bugreport')
		if self._flagFile.exists():
			self._recording = True
			self.logInfo('Flag file detected, recording errors for this run')
		else:
			self._recording = False
		self._history = list()
		self._title = ''


	@property
	def isRecording(self) -> bool:
		return self._recording


	def addToHistory(self, log: str):
		if not self._recording:
			return

		if len(self._history) <= 0:
			self._history.append('Project Alice logs')
			version = subprocess.run(f'git rev-parse HEAD', capture_output=True, text=True, shell=True).stdout.strip()
			self.logInfo(f'Git commit id: {version}')

		if len(self._history) > 2500:
			del self._history[1] # Don't delete first line, it's the git commit id

		self._history.append(log)

		if not self._title and traceback.format_exc().strip() != 'NoneType: None':
			self._title = traceback.format_exc().strip().split('\n').pop()


	def onStop(self):
		super().onStop()
		if not self._recording:
			return

		if not self._history or not self._title:
			self.logInfo('Nothing to report')
		elif not self.ConfigManager.githubAuth:
			self.logWarning('Cannot report bugs if Github user and token are not set in configs')
		else:
			title = f'[AUTO BUG REPORT] {self._title}'
			body = '\n'.join(self._history)
			data = {
				'title': title,
				'body': f'```\n{body}\n```'
			}

			request = requests.post(url=f'{constants.GITHUB_API_URL}/ProjectAlice/issues', data=json.dumps(data), auth=self.ConfigManager.githubAuth)
			if request.status_code != 201:
				self.logError(f'Something went wrong reporting a bug, status: {request.status_code}, error: {request.json()}')
			else:
				self.logInfo(f'Created new issue: {request.json()["html_url"]}')

			os.remove(self._flagFile)
