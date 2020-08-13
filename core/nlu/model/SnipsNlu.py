import json
from pathlib import Path
from subprocess import CompletedProcess

import re
import shutil

from core.commons import constants
from core.nlu.model.NluEngine import NluEngine
from core.util.Stopwatch import Stopwatch


class SnipsNlu(NluEngine):
	NAME = 'Snips NLU'
	UTTERANCE_REGEX = re.compile('{(.+?:=>.+?)}')


	def __init__(self):
		super().__init__()
		self._cachePath = Path(self.Commons.rootDir(), f'var/cache/nlu/trainingData')
		self._timer = None


	def start(self):
		super().start()
		self.Commons.runRootSystemCommand(['systemctl', 'start', 'snips-nlu'])


	def stop(self):
		super().stop()
		self.Commons.runRootSystemCommand(['systemctl', 'stop', 'snips-nlu'])


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
					} for value in entity['values']
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
		self.logInfo('Training Snips NLU')
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
			json.dump(dataset, fp, ensure_ascii=False, indent=4)

		self.logInfo('Generated dataset for training')

		# Now that we have generated the dataset, let's train in the background if we are already booted, else do it directly
		if self.ProjectAlice.isBooted:
			self.ThreadManager.newThread(name='NLUTraining', target=self.nluTrainingThread, args=[datasetFile])
		else:
			self.nluTrainingThread(datasetFile)


	def nluTrainingThread(self, datasetFile: Path):
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
				self.logError('Snips NLU training failed')
				self.MqttManager.publish(constants.TOPIC_NLU_TRAINING_STATUS, payload={'status': 'failed'})
				if not assistantPath.exists():
					self.logFatal('No NLU engine found, cannot start')

				self._timer.cancel()
				return

			if assistantPath.exists():
				shutil.rmtree(assistantPath)

			shutil.move(tempTrainingData, assistantPath)

			self.broadcast(method=constants.EVENT_NLU_TRAINED, exceptions=[constants.DUMMY], propagateToSkills=True)
			self.Commons.runRootSystemCommand(['systemctl', 'restart', 'snips-nlu'])

		self._timer.cancel()
		self.MqttManager.publish(constants.TOPIC_NLU_TRAINING_STATUS, payload={'status': 'done'})
		self.ThreadManager.getEvent('TrainAssistant').clear()
		self.logInfo(f'Snips NLU trained in {stopWatch} seconds')


	def trainingStatus(self):
		self.MqttManager.publish(constants.TOPIC_NLU_TRAINING_STATUS, payload={'status': 'training'})
		self._timer = self.ThreadManager.newTimer(interval=0.25, func=self.trainingStatus)


	@staticmethod
	def loadSlots(intent: dict) -> dict:
		return dict() if 'slots' not in intent else {
			slot['name']: slot['type']
			for slot in intent['slots']
		}
