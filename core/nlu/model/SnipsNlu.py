#  Copyright (c) 2021
#
#  This file, SnipsNlu.py, is part of Project Alice.
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
#  Last modified: 2021.05.19 at 12:56:47 CEST

import json
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from subprocess import CompletedProcess
from typing import Optional

from core.commons import constants
from core.nlu.model.NluEngine import NluEngine
from core.util.Stopwatch import Stopwatch
from core.webui.model.UINotificationType import UINotificationType


class SnipsNlu(NluEngine):
	NAME = 'Snips NLU'
	UTTERANCE_REGEX = re.compile('{(.+?:=>.+?)}')


	def __init__(self):
		super().__init__()
		self._cachePath = Path(self.Commons.rootDir(), f'var/cache/nlu/trainingData')
		self._timer = None


	def start(self):
		super().start()

		cmd = f'snips-nlu -a {self.Commons.rootDir()}/assistant --mqtt {self.ConfigManager.getAliceConfigByName("mqttHost")}:{self.ConfigManager.getAliceConfigByName("mqttPort")}'

		if self.ConfigManager.getAliceConfigByName('mqttUser'):
			cmd += f' --mqtt-username {self.ConfigManager.getAliceConfigByName("mqttUser")} --mqtt-password {self.ConfigManager.getAliceConfigByName("mqttPassword")}'

		if self.ConfigManager.getAliceConfigByName('mqttTLSFile'):
			cmd += f' --mqtt-tls-cafile {self.ConfigManager.getAliceConfigByName("mqttTLSFile")}'

		self.SubprocessManager.runSubprocess(cmd=cmd, name='SnipsNLU', autoRestart=True)


	def stop(self):
		super().stop()
		self.SubprocessManager.terminateSubprocess(name='SnipsNLU')


	def convertDialogTemplate(self, file: Path):
		self.logInfo(f'Preparing NLU training file')
		dialogTemplate = json.loads(file.read_text())

		nluTrainingSample = dict()
		nluTrainingSample['language'] = self.LanguageManager.activeLanguage
		nluTrainingSample['entities'] = dict()
		nluTrainingSample['intents'] = dict()

		for skill in dialogTemplate:
			for entity in skill['slotTypes']:
				nluTrainingSampleEntity = nluTrainingSample['entities'].setdefault(entity['name'], dict())

				nluTrainingSampleEntity['automatically_extensible'] = entity['automaticallyExtensible']
				nluTrainingSampleEntity['matching_strictness'] = entity['matchingStrictness'] or 1.0
				nluTrainingSampleEntity['use_synonyms'] = entity['useSynonyms']

				nluTrainingSampleEntity['data'] = [{
						'value'   : value['value'],
						'synonyms': value.get('synonyms', list())
					} for value in entity['values'] if value is not None
				]

			for intent in skill['intents']:
				intentName = intent['name']
				slots = self.loadSlots(intent)
				nluTrainingSample['intents'][intentName] = {'utterances': list()}

				for utterance in intent['utterances']:
					data = list()
					result = self.UTTERANCE_REGEX.split(utterance)
					if not result:
						data.append({
							'text': utterance
						})
					else:
						for match in result:
							if ':=>' not in match:
								data.append({
									'text': match
								})
								continue

							text, slotName = match.split(':=>')
							entity = slots.get(slotName, None)

							if not entity:
								self.logWarning(f'Slot named "{slotName}" with text "{text}" in utterance "{utterance}" doesn\'t have any matching slot definition, skipping to avoid NLU training failure')
								continue

							if entity.startswith('snips/'):
								nluTrainingSample['entities'][entity] = dict()

							data.append({
								'entity'   : entity,
								'slot_name': slotName,
								'text'     : text
							})

					# noinspection PyTypeChecker
					nluTrainingSample['intents'][intentName]['utterances'].append({'data': data})

		with Path(self._cachePath / f'{self.LanguageManager.activeLanguage}.json').open('w') as fp:
			json.dump(nluTrainingSample, fp, ensure_ascii=False)


	def train(self):
		if self.NluManager.training:
			self.logWarning("NLU is already training, can't train again now")
			return

		self.logInfo('Training Snips NLU')
		try:
			self.NluManager.training = True
			dataset = {
				'entities': dict(),
				'intents' : dict(),
				'language': self.LanguageManager.activeLanguage,
			}

			with Path(self._cachePath / f'{self.LanguageManager.activeLanguage}.json').open() as fp:
				trainingData = json.load(fp)
				dataset['entities'].update(trainingData['entities'])
				dataset['intents'].update(trainingData['intents'])

			datasetFile = Path('/tmp/snipsNluDataset.json')

			with datasetFile.open('w') as fp:
				json.dump(dataset, fp, ensure_ascii=False, indent='\t')

			self.logInfo('Generated dataset for training')

			# Now that we have generated the dataset, let's train in the background if we are already booted, else do it directly
			if self.ProjectAlice.isBooted:
				self.ThreadManager.newThread(name='NLUTraining', target=self.nluTrainingThread, args=[datasetFile])
			else:
				self.nluTrainingThread(datasetFile)
		except:
			self.NluManager.training = False


	def nluTrainingThread(self, datasetFile: Path):
		try:
			with Stopwatch() as stopWatch:
				self.logInfo('Begin training...')
				self._timer = self.ThreadManager.newTimer(interval=0.25, func=self.trainingStatus)

				tempTrainingData = Path('/tmp/snipsNLU')

				if tempTrainingData.exists():
					shutil.rmtree(tempTrainingData)

				training: CompletedProcess = self.Commons.runSystemCommand([f'./venv/bin/snips-nlu', 'train', str(datasetFile), str(tempTrainingData)])
				if training.returncode != 0:
					self.logError(f'Error while training Snips NLU: {training.stderr.decode()}')

				assistantPath = Path(self.Commons.rootDir(), f'trained/assistants/{self.LanguageManager.activeLanguage}/nlu_engine')

				if not tempTrainingData.exists():
					self.trainingFailed()

					if not assistantPath.exists():
						self.logFatal('No NLU engine found, cannot start')

					self._timer.cancel()
					return

				if assistantPath.exists():
					shutil.rmtree(assistantPath)

				shutil.move(tempTrainingData, assistantPath)

			self._timer.cancel()
			self.MqttManager.publish(constants.TOPIC_NLU_TRAINING_STATUS, payload={'status': 'done'})
			self.WebUIManager.newNotification(
				tipe=UINotificationType.INFO,
				notification='nluTrainingDone',
				key='nluTraining'
			)

			self.ThreadManager.getEvent('TrainAssistant').clear()
			self.logInfo(f'Snips NLU trained in {stopWatch} seconds')

			self.broadcast(method=constants.EVENT_NLU_TRAINED, exceptions=[constants.DUMMY], propagateToSkills=True)
			self.NluManager.restartEngine()
		except:
			self.trainingFailed()
		finally:
			self.NluManager.training = False


	def trainingStatus(self, dots: str = ''):
		count = dots.count('.')
		if not dots or count > 7:
			dots = '.'
		else:
			dots += '.'

		self.MqttManager.publish(constants.TOPIC_NLU_TRAINING_STATUS, payload={'status': 'training'})

		self.WebUIManager.newNotification(
			tipe=UINotificationType.INFO,
			notification='nluTraining',
			key='nluTraining',
			replaceBody=dots
		)

		self._timer = self.ThreadManager.newTimer(interval=1, func=self.trainingStatus, args=[dots])


	@staticmethod
	def loadSlots(intent: dict) -> dict:
		return dict() if 'slots' not in intent else {
			slot['name']: slot['type']
			for slot in intent['slots']
		}


	def trainingFailed(self):
		self.logError('Snips NLU training failed')
		self.MqttManager.publish(constants.TOPIC_NLU_TRAINING_STATUS, payload={'status': 'failed'})

		self.WebUIManager.newNotification(
			tipe=UINotificationType.ERROR,
			notification='nluTrainingFailed',
			key='nluTraining'
		)
