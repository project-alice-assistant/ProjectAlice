import json
import re
import shutil
import threading
import time
from pathlib import Path
from subprocess import CompletedProcess

import subprocess

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
		self._thread: threading.Thread = self.ThreadManager.newThread(name='nluEngine', target=self.run, autostart=False)
		self._flag = threading.Event()


	def start(self):
		super().start()
		self._flag.clear()
		if self._thread.is_alive():
			self._thread.join(timeout=5)

		self._thread.start()


	def stop(self):
		super().stop()
		self._flag.clear()
		if self._thread.is_alive():
			self.ThreadManager.terminateThread(name='nluEngine')


	def run(self):
		cmd = f'snips-nlu -a {self.Commons.rootDir()}/assistant --mqtt {self.ConfigManager.getAliceConfigByName("mqttHost")}:{self.ConfigManager.getAliceConfigByName("mqttPort")}'

		if self.ConfigManager.getAliceConfigByName('mqttUser'):
			cmd += f' --mqtt-username {self.ConfigManager.getAliceConfigByName("mqttUser")} --mqtt-password {self.ConfigManager.getAliceConfigByName("mqttPassword")}'

		if self.ConfigManager.getAliceConfigByName('mqttTLSFile'):
			cmd += f' --mqtt-tls-cafile {self.ConfigManager.getAliceConfigByName("mqttTLSFile")}'

		process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

		self._flag.set()
		try:
			while self._flag.is_set():
				time.sleep(0.5)
		finally:
			process.terminate()


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
					self.logError('Snips NLU training failed')
					self.MqttManager.publish(constants.TOPIC_NLU_TRAINING_STATUS, payload={'status': 'failed'})
					if not assistantPath.exists():
						self.logFatal('No NLU engine found, cannot start')

					self._timer.cancel()
					return

				if assistantPath.exists():
					shutil.rmtree(assistantPath)

				shutil.move(tempTrainingData, assistantPath)

			self._timer.cancel()
			self.MqttManager.publish(constants.TOPIC_NLU_TRAINING_STATUS, payload={'status': 'done'})
			self.ThreadManager.getEvent('TrainAssistant').clear()
			self.logInfo(f'Snips NLU trained in {stopWatch} seconds')

			self.broadcast(method=constants.EVENT_NLU_TRAINED, exceptions=[constants.DUMMY], propagateToSkills=True)
			self.NluManager.reloadNLU()
		except:
			self.MqttManager.publish(constants.TOPIC_NLU_TRAINING_STATUS, payload={'status': 'failed'})
		finally:
			self.NluManager.training = False


	def trainingStatus(self):
		self.MqttManager.publish(constants.TOPIC_NLU_TRAINING_STATUS, payload={'status': 'training'})
		self._timer = self.ThreadManager.newTimer(interval=0.25, func=self.trainingStatus)


	@staticmethod
	def loadSlots(intent: dict) -> dict:
		return dict() if 'slots' not in intent else {
			slot['name']: slot['type']
			for slot in intent['slots']
		}
