#  Copyright (c) 2021
#
#  This file, AssistantManager.py, is part of Project Alice.
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

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator

from core.base.model.Manager import Manager
from core.base.model.StateType import StateType


class AssistantManager(Manager):
	STATE = 'projectalice.core.training'


	def __init__(self):
		super().__init__()

		self._assistantPath = Path(self.Commons.rootDir(), 'assistant/assistant.json')
		if not self._assistantPath.exists():
			self.logInfo('Assistant not found, generating')
			self.linkAssistant()
			self._assistantPath = Path(self.Commons.rootDir(), 'assistant/assistant.json')
			self._assistantPath.write_text(json.dumps(self.newAssistant()))


	def onStart(self):
		super().onStart()
		self.checkAssistant()


	def clearAssistant(self):
		self._assistantPath.write_text(json.dumps(self.newAssistant()))


	def checkAssistant(self, forceRetrain: bool = False):
		self.logInfo('Checking assistant')

		if forceRetrain:
			self.logInfo('Forced assistant training')
			self.train()
			self.DialogTemplateManager.clearCache(rebuild=False)
			self.DialogTemplateManager.train()
			self.NluManager.clearCache()
			self.NluManager.train()
		elif not self._assistantPath.exists():
			self.logInfo('Assistant not found')
			self.train()
		elif not self.checkConsistency():
			self.logInfo('Assistant is not consistent, it needs training')
			self.train()

		if not self.DialogTemplateManager.checkData():
			self.DialogTemplateManager.train()
			self.NluManager.train()
		elif not self.NluManager.checkEngine():
			self.NluManager.train()


	def checkConsistency(self) -> bool:
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
			try:
				data = json.load(fp)
			except json.decoder.JSONDecodeError:
				self.logError('Found assistant to be empty or corrupted! [JSONDecodeError]')
				return False

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

		state = self.StateManager.getState(self.STATE)
		if not state:
			self.StateManager.register(self.STATE, initialState=StateType.RUNNING)
		elif state.currentState == StateType.RUNNING:
			self._logger.logInfo('Training cancelled, already running')
			return

		self.StateManager.setState(self.STATE, newState=StateType.RUNNING)

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
					self.logDebug('Skill has no intent')
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

			self._assistantPath.write_text(json.dumps(assistant, ensure_ascii=False, indent='\t', sort_keys=True))
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


	def switchLanguage(self, targetLang: str):
		"""
		Switches the assistant language to targetLang
		:param targetLang: str, the language to switch to
		:return:
		"""
		self.ConfigManager.updateAliceConfiguration(key='activeLanguage', value=targetLang)
		self.LanguageManager.restart()
		self.TalkManager.restart()
		self.ASRManager.restart()
		self.linkAssistant()
		self.checkAssistant()
