import json
from pathlib import Path

import random
import re
import shutil

from core.base.SuperManager import SuperManager
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
		SuperManager.getInstance().snipsServicesManager.runCmd(cmd='start', services=['snips-nlu'])


	def stop(self):
		super().stop()
		SuperManager.getInstance().snipsServicesManager.runCmd(cmd='stop', services=['snips-nlu'])


	def convertDialogTemplate(self, file: Path):
		self.logInfo(f'Preparing NLU training file for {file}')
		with file.open() as fp:
			dialogTemplate = json.load(fp)

		nluTrainingSample = dict()
		nluTrainingSample['language'] = file.stem
		nluTrainingSample['entities'] = dict()

		for entity in dialogTemplate['slotTypes']:
			nluTrainingSampleEntity = nluTrainingSample['entities'].setdefault(entity['name'], dict())

			nluTrainingSampleEntity['automatically_extensible'] = entity['automaticallyExtensible']
			nluTrainingSampleEntity['matching_strictness'] = entity['matchingStrictness'] or 1.0
			nluTrainingSampleEntity['use_synonyms'] = entity['useSynonyms']

			nluTrainingSampleEntity['data'] = [{
					'value'   : value['value'],
					'synonyms': value.get('synonyms', list())
				} for value in entity['values']
			]

		nluTrainingSample['intents'] = dict()
		for intent in dialogTemplate['intents']:
			intentName = intent['name']
			slots = self.loadSlots(intent)
			nluTrainingSample['intents'].setdefault(intentName, {'utterances': list()})

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
						entity = slots.get(slotName, 'Unknown')

						if entity.startswith('snips/'):
							nluTrainingSample['entities'][entity] = dict()

						data.append({
							'entity'   : entity,
							'slot_name': slotName,
							'text'     : text
						})

				# noinspection PyTypeChecker
				nluTrainingSample['intents'][intentName]['utterances'].append({'data': data})

			with Path(self._cachePath, f'{dialogTemplate["skill"]}_{file.stem}.json').open('w') as fp:
				json.dump(nluTrainingSample, fp, ensure_ascii=False, indent=4)


	def train(self):
		self.logInfo('Training Snips NLU')
		dataset = {
			'entities': dict(),
			'intents' : dict(),
			'language': self.LanguageManager.activeLanguage,
		}

		for file in self._cachePath.glob(f'*_{self.LanguageManager.activeLanguage}.json'):
			with file.open() as fp:
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
			self._timer = self.ThreadManager.newTimer(interval=10, func=self.trainingStatus)

			tempTrainingData = Path('/tmp/snipsNLU')

			if tempTrainingData.exists():
				shutil.rmtree(tempTrainingData)

			self.Commons.runSystemCommand([f'./venv/bin/snips-nlu', 'train', str(datasetFile), str(tempTrainingData)])

			assistantPath = Path(self.Commons.rootDir(), f'trained/assistants/assistant_{self.LanguageManager.activeLanguage}/nlu_engine')

			if not tempTrainingData.exists():
				self.logError('Snips NLU training failed')
				if not assistantPath.exists():
					self.logFatal('No NLU engine found, cannot start')

				self._timer.cancel()
				return

			if assistantPath.exists():
				shutil.rmtree(assistantPath)

			tempTrainingData.rename(assistantPath)

			self.broadcast(method=constants.EVENT_NLU_TRAINED, exceptions=[constants.DUMMY], propagateToSkills=True)
			self.SnipsServicesManager.runCmd(cmd='restart', services=['snips-nlu'])

		self._timer.cancel()
		self.ThreadManager.getEvent('TrainAssistant').clear()
		self.logInfo(f'Snips NLU trained in {stopWatch} seconds')


	def trainingStatus(self):
		self.logInfo(random.choice(['Still training...', "Don't worry, I'm still training", 'Still on it', 'Takes time, I know', 'Working...', 'Working as fast as I can!']))
		self._timer = self.ThreadManager.newTimer(interval=10, func=self.trainingStatus)


	@staticmethod
	def loadSlots(intent: dict) -> dict:
		return dict() if 'slots' not in intent else {
			slot['name']: slot['type']
			for slot in intent['slots']
		}
