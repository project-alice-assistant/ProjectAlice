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
from pathlib import Path
from subprocess import CompletedProcess

from core.nlu.model.NluEngine import NluEngine


class SnipsNlu(NluEngine):
	NAME = 'Snips NLU'
	UTTERANCE_REGEX = re.compile('{(.+?:=>.+?)}')


	def __init__(self):
		super().__init__()
		self._cachePath = Path(self.Commons.rootDir(), f'var/cache/nlu/trainingData')


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
		nluTrainingSample['language'] = self.getLanguage()
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

		with Path(self._cachePath / f'{self.getLanguage()}.json').open('w') as fp:
			json.dump(nluTrainingSample, fp, ensure_ascii=False)


	def train(self, forceLocalTraining: bool = False):
		if not super().train(forceLocalTraining):
			return

		try:
			dataset = {
				'entities': dict(),
				'intents' : dict(),
				'language': self.getLanguage()
			}

			with Path(self._cachePath / f'{self.getLanguage()}.json').open() as fp:
				trainingData = json.load(fp)
				dataset['entities'].update(trainingData['entities'])
				dataset['intents'].update(trainingData['intents'])

			self.logInfo('Generated dataset for training')
			# Now that we have generated the dataset, let's train in the background if we are already booted, else do it directly
			if self.ConfigManager.getAliceConfigByName('delegateNluTraining') and not forceLocalTraining:
				self.NluManager.startOffshoreTraining(dataset)
			else:
				datasetFile = Path('/tmp/snipsNluDataset.json')
				with datasetFile.open('w') as fp:
					json.dump(dataset, fp, ensure_ascii=False, indent='\t')

				if self.ProjectAlice.isBooted:
					self.ThreadManager.newThread(name='NLUTraining', target=self.nluTrainingThread, args=[datasetFile])
				else:
					self.nluTrainingThread(datasetFile)
		except Exception as e:
			self.trainingFailed(str(e))


	def nluTrainingThread(self, datasetFile: Path):
		try:
			self.logInfo('Begin training...')
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

				return
			self.trainingFinished(trainedData=tempTrainingData)
		except Exception as e:
			self.trainingFailed(str(e))


	@staticmethod
	def loadSlots(intent: dict) -> dict:
		return dict() if 'slots' not in intent else {
			slot['name']: slot['type']
			for slot in intent['slots']
		}


	def trainingFinished(self, trainedData: Path):
		assistantPath = Path(self.Commons.rootDir(), f'trained/assistants/{self.LanguageManager.activeLanguage}/nlu_engine')
		if assistantPath.exists():
			shutil.rmtree(assistantPath)
		shutil.move(trainedData, assistantPath)

		super().trainingFinished(trainedData=trainedData)
