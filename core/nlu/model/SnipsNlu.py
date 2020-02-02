import json
from pathlib import Path

from core.base.SuperManager import SuperManager
from core.nlu.model.NluEngine import NluEngine


class SnipsNlu(NluEngine):
	NAME = 'Snips NLU'


	def __init__(self):
		super().__init__()


	def start(self):
		super().start()
		SuperManager.getInstance().snipsServicesManager.runCmd(cmd='start', services=['snips-nlu'])


	def stop(self):
		super().stop()
		SuperManager.getInstance().snipsServicesManager.runCmd(cmd='stop', services=['snips-nlu'])


	def convertDialogTemplate(self, file: Path):
		print(f'Converting {str(file)}')
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
						'synonyms': value['synonyms'] if 'synonyms' in value else []
					})
				nluTrainingSample['entities'][entity['name']]['data'] = values

			with Path(self.Commons.rootDir(), f'var/cache/nlu/trainingData/{dialogTemplate["skill"]}_{file.stem}.json').open('w') as fpp:
				fpp.write(json.dumps(nluTrainingSample, indent=4))
