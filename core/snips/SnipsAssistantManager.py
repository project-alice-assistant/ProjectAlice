import json
from datetime import datetime
from pathlib import Path

from core.base.model.Manager import Manager


class SnipsAssistantManager(Manager):

	def __init__(self):
		super().__init__()
		self._assistantPath = Path(self.Commons.rootDir(), f'assistant/assistant.json')


	def onStart(self):
		super().onStart()
		self.checkAssistant()


	def checkAssistant(self):
		self.logInfo('Checking assistant')
		if not self._assistantPath.exists():
			self.logInfo('Assistant not found, generating')
			self.train()
		else:
			self.logInfo('Assistant existing, check consistency')
			if not self.checkConsistency():
				self.logInfo('Assistant is not consistent, needs training')
				self.train()


	def checkConsistency(self) -> bool:
		if not self._assistantPath.exists():
			return False

		existingIntents = set()
		existingSlots = set()

		for skillResource in self.DialogTemplateManager.skillResource():

			with skillResource.open() as resource:
				data = json.load(resource)

			if 'intents' not in data:
				continue

			for intent in data['intents']:
				existingIntents.add(intent['name'])

				if not intent['slots']:
					continue

				for slot in intent['slots']:
					existingSlots.add(slot['name'])

		with self._assistantPath.open() as fp:
			data = json.load(fp)
			for intent in data['intents']:
				if intent['name'] not in existingIntents:
					return False

				for slot in intent['slots']:
					if slot['name'] not in existingSlots:
						return False

		self.logInfo('Assistant seems consistent')
		return True


	def train(self):
		self.logInfo('Training assistant')

		try:
			assistant = self.generateAssistant()
			intents = dict()
			slots = dict()

			for skillResource in self.DialogTemplateManager.skillResource():

				with skillResource.open() as fp:
					data = json.load(fp)

				if 'intents' not in data:
					self.logDebug(f'Skill "{skillResource["skill"]}" has no intent')
					continue

				for intent in data['intents']:
					if intent['name'] in intents:
						self.logWarning(f'Intent "{intent["name"]}" is duplicated')
						continue

					intents[intent['name']] = {
						'id'              : intent['name'],
						'type'            : 'registry',
						'version'         : '0.1.0',
						'language'        : self.LanguageManager.activeLanguage,
						'slots'           : list(),
						'name'            : intent['name'],
						'enabledByDefault': intent['enabledByDefault']
					}

					if not intent['slots']:
						continue

					for slot in intent['slots']:
						if slot['type'] not in slots:
							intentSlot = {
								'name'           : slot['name'],
								'id'             : self.Commons.randomString(9),
								'entityId'       : f'entity_{self.Commons.randomString(11)}',
								'missingQuestion': slot['missingQuestion'],
								'required'       : slot['required']
							}
							slots[slot['type']] = intentSlot
						else:
							intentSlot = {
								'name'           : slot['name'],
								'id'             : self.Commons.randomString(9),
								'entityId'       : slots[slot['type']]['entityId'],
								'missingQuestion': slot['missingQuestion'],
								'required'       : slot['required']
							}

						intents[intent['name']]['slots'].append(intentSlot)

			assistant['intents'] = [intent for intent in intents.values()]

			self.Commons.runRootSystemCommand(['ln', '-sfn', self.Commons.rootDir() + f'/trained/assistants/assistant_{self.LanguageManager.activeLanguage}', self.Commons.rootDir() + '/assistant'])

			with self._assistantPath.open('w') as fp:
				fp.write(json.dumps(assistant, ensure_ascii=False, indent=4, sort_keys=True))

			self.Commons.runRootSystemCommand(['ln', '-sfn', self.Commons.rootDir() + f'/system/sounds/{self.LanguageManager.activeLanguage}/start_of_input.wav', self.Commons.rootDir() + '/assistant/custom_dialogue/sound/start_of_input.wav'])
			self.Commons.runRootSystemCommand(['ln', '-sfn', self.Commons.rootDir() + f'/system/sounds/{self.LanguageManager.activeLanguage}/end_of_input.wav', self.Commons.rootDir() + '/assistant/custom_dialogue/sound/end_of_input.wav'])
			self.Commons.runRootSystemCommand(['ln', '-sfn', self.Commons.rootDir() + f'/system/sounds/{self.LanguageManager.activeLanguage}/error.wav', self.Commons.rootDir() + '/assistant/custom_dialogue/sound/error.wav'])

			self.broadcast(method='snipsAssistantInstalled', exceptions=[self.name], propagateToSkills=True)
			self.logInfo(f'Assistant trained with {len(intents)} intents with a total of {len(slots)} slots')
		except Exception as e:
			self.broadcast(method='snipsAssistantFailedTraining', exceptions=[self.name], propagateToSkills=True)
			if not self._assistantPath.exists():
				self.logFatal('Assistant failed training and no assistant existing, stopping here, sorry....')


	def generateAssistant(self) -> dict:
		assistant = {
			'id'              : f'proj_{self.Commons.randomString(11)}',
			'name'            : f'ProjectAlice_{self.LanguageManager.activeLanguage}',
			'analyticsEnabled': False,
			'heartbeatEnabled': False,
			'language'        : self.LanguageManager.activeLanguage,

			# Declare as google so snips doesn't try to find the snips-asr service
			'asr'             : {'type': 'google'},

			'platform'        : {'type': 'raspberrypi'},
			'createdAt'       : datetime.utcnow().isoformat() + 'Z',
			'hotword'         : 'hey_snips',
			'version'         : {'nluModel': '0.20.1'},
			'intents'         : list()
		}

		return assistant
