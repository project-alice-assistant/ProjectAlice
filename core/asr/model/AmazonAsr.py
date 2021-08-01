#  Copyright (c) 2021
#
#  This file, AmazonAsr.py, is part of Project Alice.
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

from core.asr.model.Asr import Asr

try:
	from boto3 import client
except:
	pass # Auto installed



class AmazonAsr(Asr):

	NAME = 'Amazon Asr'
	DEPENDENCIES = {
		'system': [],
		'pip': 	  {
			'boto3==1.17.85'
		}
	}

	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = True

		self._client: client = None


	def onStart(self):
		super().onStart()
		self._client = client(
			'transcribe',
			region_name=self.ConfigManager.getAliceConfigByName('awsRegion'),
			aws_access_key_id=self.ConfigManager.getAliceConfigByName('awsAccessKey'),
			aws_secret_access_key=self.ConfigManager.getAliceConfigByName('awsSecretKey')
		)
