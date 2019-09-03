import typing

import hashlib
import re

from core.snips import SamkillaManager
from core.ProjectAliceExceptions import  HttpError, IntentError
from core.snips.samkilla.gql.intents.deleteIntent import deleteIntent
from core.snips.samkilla.gql.intents.publishIntent import publishIntent
from core.snips.samkilla.gql.intents.queries import fullIntentQuery, intentsByUserIdWithUsageQuery
from core.snips.samkilla.gql.skills.patchSkillIntents import patchSkillIntents

UTTERANCES_DEFINITION_REGEX = re.compile(r'{(.*?):=>(.*?)}')


class Intent:
	GLUE_SLOT_WORD = ":=>"


	def __init__(self, ctx: SamkillaManager):
		self._ctx = ctx
		self._cacheInit = False
		self._intentsCache = {'cacheId': dict(), 'cacheName': dict()}


	def getIntentByUserIdAndIntentName(self, userId: str, intentName: str) -> dict:
		return self._intentsCache['cacheName'].get(intentName.lower(), self.listIntentsByUserId(userId, intentFilter=intentName, intentFilterAttribute='name'))


	def getIntentByUserIdAndIntentId(self, userId: str, intentId: str) -> dict:
		return self._intentsCache['cacheId'].get(intentId, self.listIntentsByUserId(userId, intentFilter=intentId))


	def listIntentsByUserId(self, userId: str, intentFilter: str = None, languageFilter: str = None, intentFilterAttribute: str = 'id', returnAllCacheIndexedBy: str = None) -> dict:
		variables = {'userId': userId}

		if languageFilter:
			variables['lang'] = languageFilter

		gqlRequest = [{
			'operationName': 'IntentsByUserIdWithUsageQuery',
			'variables'    : variables,
			'query'        : intentsByUserIdWithUsageQuery
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)

		self._cacheInit = True

		for intent in response['intents']:
			self._intentsCache['cacheId'][intent['id']] = intent
			self._intentsCache['cacheName'][intent['name'].lower()] = intent

		if returnAllCacheIndexedBy:
			key = returnAllCacheIndexedBy[0].upper() + returnAllCacheIndexedBy[1:]
			return self._intentsCache['cache' + key]

		if intentFilter:
			if intentFilterAttribute == 'id':
				return self._intentsCache['cacheId'][intentFilter]
			elif intentFilterAttribute == 'name':
				return self._intentsCache['cacheName'][intentFilter.lower()]

		return response['intents']


	def listIntentsByUserIdAndSkillId(self, userId: str, skillId: str, languageFilter: str = None, indexedBy: str = None, fromCache: bool = False) -> typing.Iterable:
		if fromCache and self._cacheInit:
			intents = self._intentsCache['cacheId'].values()
		else:
			intents = self.listIntentsByUserId(userId=userId, languageFilter=languageFilter)

		skillIntents = list()
		indexedSkillIntents = dict()

		for intent in intents:
			if intent['usedIn']:
				for skillMeta in intent['usedIn']:
					if skillMeta['skillId'] == skillId:
						if indexedBy:
							indexedSkillIntents[intent[indexedBy]] = intent
						else:
							skillIntents.append(intent)

		if indexedBy:
			return indexedSkillIntents

		return skillIntents


	def listUtterancesByIntentId(self, intentId: str) -> list:
		variables = {'intentId': intentId}

		gqlRequest = [{
			'operationName': 'FullIntentQuery',
			'variables'    : variables,
			'query'        : fullIntentQuery
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)

		return response['intent']['customIntentData']['utterances']


	def create(self, userId: str, language: str, skillId: str, name: str = 'Untitled', description: str = '', enabledByDefault: bool = True,
			   attachToSkill: bool = True, typeEntityMatching: dict = None, slotsDefinition: dict = None, utterancesDefinition: list = None) -> str:
		"""
		Warning: mind the language parameter if the skill language is EN, intent must set language to EN
		no error will be shown and the skill won't be created
		"""

		structuredSlots, entities = self.formatSlotsAndEntities(typeEntityMatching, slotsDefinition)
		structuredUtterances, exempleQueries = self.formatUtterancesAndExempleQueries(utterancesDefinition)

		finalStructuredUtterances = list()

		if structuredUtterances:
			finalStructuredUtterances = structuredUtterances
		else:
			finalStructuredUtterances.append({'data': [{'range': {'start': 0, 'end': 0}, 'text': ''}]})

		gqlRequest = [{
			'operationName': 'publishIntent',
			'variables'    : {
				'input': {
					'config' : {
						'author'          : self._ctx.userEmail,
						'description'     : description,
						'displayName'     : name,
						'enabledByDefault': enabledByDefault,
						'exampleQueries'  : exempleQueries,
						'language'        : language,
						'name'            : name,
						'private'         : True,
						'slots'           : structuredSlots,
						'version'         : '0'
					},
					'dataset': {
						'entities'  : entities,
						'language'  : language,
						'utterances': finalStructuredUtterances
					}
				}
			},
			'query'        : publishIntent
		}]

		try:
			response = self._ctx.postGQLBrowserly(gqlRequest)
		except HttpError as he:
			if he.status == 409:
				self._ctx.log("Duplicate intent with name {}".format(name))
				intentDuplicate = self.getIntentByUserIdAndIntentName(userId, name)

				if intentDuplicate:
					if 'usedIn' in intentDuplicate and intentDuplicate['usedIn']:
						for skillItem in intentDuplicate['usedIn']:
							self.removeFromSkill(intentId=intentDuplicate['id'], skillId=skillItem['skillId'], userId=userId, deleteAfter=False)
					self.delete(intentId=intentDuplicate['id'])
					return self.create(userId, language, skillId, name, description, enabledByDefault, attachToSkill, typeEntityMatching, slotsDefinition, utterancesDefinition)

			raise he

		createdIntentId = response['publishIntent']['id']

		if attachToSkill:
			self.attachToSkill(userId=userId, skillId=skillId, intentId=createdIntentId, languageFilter=language)

		return createdIntentId


	def attachToSkill(self, userId: str, skillId: str, intentId: str, languageFilter: str = None):
		existingIntents = self.listIntentsByUserIdAndSkillId(userId=userId, skillId=skillId, languageFilter=languageFilter)
		variablesIntents = [{'id': intentId}]

		for existingIntent in existingIntents:
			variablesIntents.append({'id': existingIntent['id']})

		gqlRequest = [{
			'operationName': 'patchSkillIntents',
			'variables'    : {
				'input': {
					'id'     : skillId,
					'intents': variablesIntents
				}
			},
			'query'        : patchSkillIntents
		}]
		self._ctx.postGQLBrowserly(gqlRequest, rawResponse=True)


	def removeFromSkill(self, userId: str, skillId: str, intentId: str, languageFilter: str = None, deleteAfter: bool = True):
		existingIntents = self.listIntentsByUserIdAndSkillId(userId=userId, skillId=skillId, languageFilter=languageFilter)

		variablesIntents = list()

		for existingIntent in existingIntents:
			if existingIntent['id'] != intentId:
				variablesIntents.append({'id': existingIntent['id']})

		gqlRequest = [{
			'operationName': 'patchSkillIntents',
			'variables'    : {
				'input': {
					'id'     : skillId,
					'intents': variablesIntents
				}
			},
			'query'        : patchSkillIntents
		}]
		self._ctx.postGQLBrowserly(gqlRequest, rawResponse=True)

		if deleteAfter:
			self.delete(intentId=intentId)


	def delete(self, intentId: str):
		gqlRequest = [{
			'operationName': 'deleteIntent',
			'variables'    : {'intentId': intentId},
			'query'        : deleteIntent
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest, rawResponse=True)
		return response


	def edit(self, intentId: str, userId: str, language: str = None, skillId: str = None, name: str = None, description: str = None, enabledByDefault: bool = True,
			 attachToSkill: bool = False, typeEntityMatching: dict = None, slotsDefinition: dict = None, utterancesDefinition: list = None):
		structuredSlots, entities = self.formatSlotsAndEntities(typeEntityMatching, slotsDefinition)
		structuredUtterances, exempleQueries = self.formatUtterancesAndExempleQueries(utterancesDefinition)

		intent = self.getIntentByUserIdAndIntentId(userId=userId, intentId=intentId)

		if not intent:
			raise IntentError(4003, "Intent {} doesn't exist".format(intentId), ['intent'])

		if name: intent['name'] = name
		if description: intent['description'] = description
		if enabledByDefault: intent['enabledByDefault'] = enabledByDefault

		gqlRequest = [{
			'operationName': 'publishIntent',
			'variables'    : {
				'intentId': intentId,
				'input'   : {
					'config' : {
						'author'          : intent['author'],
						'description'     : intent['description'],
						'displayName'     : intent['displayName'],
						'enabledByDefault': intent['enabledByDefault'],
						'language'        : intent['language'],
						'exampleQueries'  : exempleQueries,
						'slots'           : structuredSlots,
						'version'         : intent['version'],
						'name'            : intent['name'],
						'private'         : True,
					},
					'dataset': {
						'entities'  : entities,
						'language'  : intent['language'],
						'utterances': structuredUtterances
					}
				}
			},
			'query'        : publishIntent
		}]
		self._ctx.postGQLBrowserly(gqlRequest, rawResponse=True)

		if attachToSkill:
			self.attachToSkill(userId=userId, skillId=skillId, intentId=intentId, languageFilter=language)


	def formatSlotsAndEntities(self, typeEntityMatching: dict, slotsDefinition: dict) -> tuple:
		entities = list()
		structuredSlots = list()

		for slot in slotsDefinition:
			snipsSpecialSlot = slot['type'].startswith('snips/')
			slotEntityId = slot['type'] if snipsSpecialSlot else typeEntityMatching[slot['type']]['entityId']

			entities.append({'id': slotEntityId, 'name': slotEntityId if snipsSpecialSlot else slot['type']})

			structuredSlots.append({
				'entityId'       : slotEntityId,
				'id'             : self.hashSlotName(slotName=slot['name']),
				'missingQuestion': slot['missingQuestion'],
				'name'           : slot['name'],
				'description'    : slot['description'],
				'required'       : slot['required'],
				'parameters'     : None
			})

		return structuredSlots, entities


	def formatUtterancesAndExempleQueries(self, utterances: list) -> tuple:
		exempleQueries = list()
		structuredUtterances = list()

		for utterance in utterances:
			items = UTTERANCES_DEFINITION_REGEX.findall(utterance)

			formattedTextUtterance = utterance
			formattedParsedUtterance = utterance
			data = list()

			lastPieceIndex = 0
			sumIndexOffset = 0
			counterItems = 0
			maxItems = len(items)

			for item in items:
				wordExemple = item[0]
				wordSlotName = item[1]

				keySlot = '{' + wordExemple + self.GLUE_SLOT_WORD + wordSlotName + '}'
				keyDummy = ''.join(['0'] * len(keySlot))

				# Text
				formattedTextUtterance = formattedTextUtterance.replace(keySlot, wordExemple, 1)
				lenCleanTextUtterance = len(formattedTextUtterance)

				# Parsed
				indexOffset = len(keySlot) - len(wordExemple)
				wordSlotIndexStart = formattedParsedUtterance.find(keySlot)
				wordSlotIndexEnd = wordSlotIndexStart + len(wordExemple)

				formattedWordSlotIndexStart = wordSlotIndexStart - sumIndexOffset
				formattedWordSlotIndexEnd = wordSlotIndexEnd - sumIndexOffset

				# for next parse processing
				formattedParsedUtterance = formattedParsedUtterance.replace(keySlot, keyDummy, 1)

				if formattedWordSlotIndexStart != 0:
					previousText = formattedTextUtterance[lastPieceIndex:formattedWordSlotIndexStart]
					data.append(
						{'text': previousText, 'range': {'start': lastPieceIndex, 'end': formattedWordSlotIndexStart}}
					)

				lastPieceIndex = formattedWordSlotIndexEnd
				sumIndexOffset += indexOffset
				counterItems += 1

				data.append({'slot_id': self.hashSlotName(slotName=wordSlotName), 'slot_name': wordSlotName, 'text': wordExemple,
							 'range'  : {'start': formattedWordSlotIndexStart, 'end': formattedWordSlotIndexEnd}})

				if counterItems == maxItems and lastPieceIndex < lenCleanTextUtterance:
					endText = formattedTextUtterance[lastPieceIndex:lenCleanTextUtterance]
					data.append({'text': endText, 'range': {'start': lastPieceIndex, 'end': lenCleanTextUtterance}})

			if not data:
				data.append({'text': formattedTextUtterance, 'range': {'start': 0, 'end': len(formattedTextUtterance)}})

			structuredUtterances.append({'data': data})
			exempleQueries.append(formattedTextUtterance)

		return structuredUtterances, exempleQueries[0:10]


	@staticmethod
	def hashSlotName(slotName: str) -> str:
		return hashlib.sha512(slotName.encode('utf-8')).hexdigest()[0:9]
