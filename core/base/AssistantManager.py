import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator

import os

from core.base.model.Manager import Manager


class AssistantManager(Manager):

	def __init__(self):
		super().__init__()

		self._assistantPath = Path(self.Commons.rootDir(), f'assistant/assistant.json')
		if not self._assistantPath.exists():
			self.logInfo('Assistant not found, generating')
			self.linkAssistant()
			self._assistantPath = Path(self.Commons.rootDir(), f'assistant/assistant.json')
			self._assistantPath.write_text(json.dumps(self.newAssistant()))


	def onStart(self):
		super().onStart()
		self.checkAssistant()


	def clearAssistant(self):
		self._assistantPath.write_text(json.dumps(self.newAssistant()))


	def checkAssistant(self, forceRetrain: bool = False):
		self.logInfo('Checking assistant')
		if not self.checkConsistency() or forceRetrain:
			self.logInfo('Assistant is not consistent, it needs training')
			self.train()
			self.DialogTemplateManager.train()
			self.NluManager.train()
		else:
			if not self.NluManager.checkData():
				self.NluManager.train()


	def checkConsistency(self) -> bool:
		if not self._assistantPath.exists() or not self.DialogTemplateManager.checkData():
			return False

		existingIntents: Dict[str, dict] = dict()
		existingSlots: Dict[str, set] = dict()

		for skillResource in self.skillResource():
			data = json.loads(skillResource.read_text())

			if 'intents' not in data:
				continue

			for intent in data['intents']:
				existingIntents[intent['name']] = intent

				if not intent['enabledByDefault']:
					self.DialogManager.addDisabledByDefaultIntent(intent['name'])
				else:
					self.DialogManager.addEnabledByDefaultIntent(intent['name'])

				if 'slots' not in intent or not intent['slots']:
					continue

				for slot in intent['slots']:
					existingSlots.setdefault(intent['name'], set())
					existingSlots[intent['name']].add(slot['name'])

		declaredIntents = dict()
		declaredSlots = dict()
		passed = True
		with self._assistantPath.open() as fp:
			data = json.load(fp)
			for intent in data['intents']:
				declaredIntents[intent['name']] = intent

				if intent['name'] not in existingIntents:
					passed = False

				for slot in intent['slots']:
					declaredSlots.setdefault(intent['name'], dict())
					declaredSlots[intent['name']][slot['name']] = slot

					if intent['name'] not in existingSlots or slot['name'] not in existingSlots[intent['name']]:
						passed = False

		for intentName, intent in existingIntents.items():
			if intentName not in declaredIntents:
				passed = False
				break

			if 'slots' not in intent or not intent['slots']:
				continue

			for slot in intent['slots']:
				if intentName not in declaredSlots:
					passed = False
					break

				if slot['name'] not in declaredSlots[intentName]:
					passed = False
					break

		if passed:
			self.logInfo('Assistant seems consistent')
		else:
			self.logInfo('Found some inconsistencies in assistant')

		return passed


	def train(self):
		self.logInfo('Training assistant')

		try:
			assistant = self.newAssistant()
			intents = dict()
			slots = dict()
			randoms = set()

			# When slots of the same entity id (type) wear the same name, their id is identical, so we need to
			# keep a track about entity ids, names and type
			entityVSType = dict()

			for skillResource in self.skillResource():

				with skillResource.open() as fp:
					data = json.load(fp)

				if 'intents' not in data:
					self.logDebug(f'Skill has no intent')
					continue

				for intent in data['intents']:
					if intent['name'] in intents:
						self.logWarning(f'Intent "{intent["name"]}" is duplicated')
						continue

					if not intent['enabledByDefault']:
						self.DialogManager.addDisabledByDefaultIntent(intent['name'])
					else:
						self.DialogManager.addEnabledByDefaultIntent(intent['name'])

					intents[intent['name']] = {
						'id'              : intent['name'],
						'type'            : 'registry',
						'version'         : '0.1.0',
						'language'        : self.LanguageManager.activeLanguage,
						'slots'           : list(),
						'name'            : intent['name'],
						'enabledByDefault': intent['enabledByDefault']
					}

					if 'slots' not in intent or not intent['slots']:
						continue

					for slot in intent['slots']:
						rand9 = self.Commons.randomString(9)
						while rand9 in randoms:
							rand9 = self.Commons.randomString(9)
						randoms.add(rand9)

						rand11 = self.Commons.randomString(11)
						while rand11 in randoms:
							rand11 = self.Commons.randomString(11)
						randoms.add(rand11)

						if slot['type'] not in slots:
							intentSlot = {
								'name'           : slot['name'],
								'id'             : rand9,
								'entityId'       : f'entity_{rand11}',
								'missingQuestion': slot['missingQuestion'],
								'required'       : slot['required']
							}
							slots[slot['type']] = intentSlot
							entityVSType[f'{slot["type"]}_{slot["name"]}'] = f'{rand9}'
						else:

							# Check if a slot with same type and name already exists and use its id else use the new random
							slotId = entityVSType.get(f'{slot["type"]}_{slot["name"]}', rand9)

							intentSlot = {
								'name'           : slot['name'],
								'id'             : slotId,
								'entityId'       : slots[slot['type']]['entityId'],
								'missingQuestion': slot['missingQuestion'],
								'required'       : slot['required']
							}

						intents[intent['name']]['slots'].append(intentSlot)

			assistant['intents'] = [intent for intent in intents.values()]

			self._assistantPath.write_text(json.dumps(assistant, ensure_ascii=False, indent=4, sort_keys=True))
			self.linkAssistant()

			self.broadcast(method='snipsAssistantInstalled', exceptions=[self.name], propagateToSkills=True)
			self.logInfo(f'Assistant trained with {len(intents)} intents and a total of {len(slots)} slots')
		except Exception as e:
			self.broadcast(method='snipsAssistantFailedTraining', exceptions=[self.name], propagateToSkills=True)
			if not self._assistantPath.exists():
				self.logFatal(f'Assistant failed training and no assistant existing, stopping here, sorry.... What happened? {e}')


	def linkAssistant(self):
		Path(self.Commons.rootDir(), f'trained/assistants/{self.LanguageManager.activeLanguage}').mkdir(parents=True, exist_ok=True)
		os.symlink(src=f'{self.Commons.rootDir()}/trained/assistants/{self.LanguageManager.activeLanguage}', dst=f'{self.Commons.rootDir()}/assistant', target_is_directory=True)


	def newAssistant(self) -> dict:
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


	def skillResource(self) -> Generator[Path, None, None]:
		for skillName, skillInstance in self.SkillManager.allWorkingSkills.items():
			resource = skillInstance.getResource(f'dialogTemplate/{self.LanguageManager.activeLanguage}.json')
			if not resource.exists():
				continue

			yield resource
