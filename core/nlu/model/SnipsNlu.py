import json
from pathlib import Path

import re

from core.base.SuperManager import SuperManager
from core.nlu.model.NluEngine import NluEngine


class SnipsNlu(NluEngine):
	NAME = 'Snips NLU'
	UTTERANCE_REGEX = re.compile('(.*?){(.+?:=>.+?)}(.*?)')
	demo = "how much is {115:=>Left} {+:=>Function} {996:=>Right}"


	def __init__(self):
		super().__init__()
		self._cachePath = Path(self.Commons.rootDir(), f'var/cache/nlu/trainingData')


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
			nluTrainingSample['intents'] = dict()

			for entity in dialogTemplate['slotTypes']:
				nluTrainingSample['entities'].setdefault(entity['name'], dict())['automatically_extensible'] = entity['automaticallyExtensible']
				nluTrainingSample['entities'][entity['name']]['matching_strictness'] = 1.0 if not entity['matchingStrictness'] else entity['matchingStrictness']
				nluTrainingSample['entities'][entity['name']]['use_synonyms'] = entity['useSynonyms']

				values = list()
				for value in entity['values']:
					values.append({
						'value'   : value['value'],
						'synonyms': value['synonyms'] if 'synonyms' in value else list()
					})
				nluTrainingSample['entities'][entity['name']]['data'] = values

			nluTrainingSample['intents'] = dict()
			for intent in dialogTemplate['intents']:
				slots = self.loadSlots(intent)
				nluTrainingSample['intents'].setdefault(intent['name'], dict()).setdefault('utterances', list())

				for utterance in intent['utterances']:
					data = list()
					result = re.findall(self.UTTERANCE_REGEX, utterance)
					if not result:
						continue

					for dataset in result:
						for match in dataset:
							if not match:
								continue

							if not ':=>' in match:
								data.append({
									'text': match
								})
							else:
								slotName = match.split(':=>')[1]
								entity = slots[slotName] if slotName in slots else 'Unknown'

								if entity.startswith('snips/'):
									nluTrainingSample['entities'][entity] = dict()

								data.append({
									'entity'   : entity,
									'slot_name': slotName,
									'text'     : match.split(':=>')[0]
								})

					# noinspection PyTypeChecker
					nluTrainingSample['intents'][intent['name']]['utterances'].append({'data': data})

			with Path(self._cachePath, f'{dialogTemplate["skill"]}_{file.stem}.json').open('w') as fpp:
				fpp.write(json.dumps(nluTrainingSample, indent=4))


	def train(self):
		self.logInfo('Training Snips NLU')
		dataset = {
			'entities': dict(),
			'intents' : dict(),
			'language': self.LanguageManager.activeLanguage,
		}

		for file in self._cachePath.glob('*.json'):
			if not f'_{self.LanguageManager.activeLanguage}' in file.stem:
				continue

			with file.open() as fp:
				trainingData = json.load(fp)
				dataset['entities'].update(trainingData['entities'])
				dataset['intents'].update(trainingData['intents'])

		datasetFile = Path('/tmp/snipsNluDataset.json')
		with datasetFile.open('w') as fp:
			fp.write(json.dumps(dataset, indent=4))

		self.logInfo('Generated dataset for training')
		self.logInfo('Begin training...')
		self.Commons.runSystemCommand([f'./venv/bin/snips-nlu', 'train', str(datasetFile), 'trainedNlu'])
		self.logInfo('Training done!')


	@staticmethod
	def loadSlots(intent: dict) -> dict:
		result = dict()
		for slot in intent['slots']:
			result[slot['name']] = slot['type']

		return result
