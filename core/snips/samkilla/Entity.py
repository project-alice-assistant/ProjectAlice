# -*- coding: utf-8 -*-
import typing

from core.snips import SamkillaManager
from core.snips.samkilla.gql.entities.createIntentEntity import createIntentEntity
from core.snips.samkilla.gql.entities.deleteIntentEntity import deleteIntentEntity
from core.snips.samkilla.gql.entities.patchIntentEntity import patchIntentEntity
from core.snips.samkilla.gql.entities.queries import customEntitiesWithUsageQuery, fullCustomEntityQuery


class Entity:

	def __init__(self, ctx: SamkillaManager):
		self._ctx = ctx
		self._cacheInit = False
		self._entitiesCache = {'cacheId': dict(), 'cacheName': dict()}


	def getEntityByUserEmailAndEntityName(self, userEmail: str, entityName: str) -> str:
		return self._entitiesCache['cacheName'].get(entityName, self.listEntitiesByUserEmail(userEmail, entityFilter=entityName, entityFilterAttribute='name'))


	def getEntityByUserEmailAndEntityId(self, userEmail: str, entityId: str) -> str:
		return self._entitiesCache['cacheId'].get(entityId, self.listEntitiesByUserEmail(userEmail, entityFilter=entityId))


	def listEntitiesByUserEmail(self, userEmail: str, entityFilter: str = None, languageFilter: str = None, entityFilterAttribute: str = 'id', returnAllCacheIndexedBy: list = None) -> dict:
		variables = {'email': userEmail}

		if languageFilter:
			variables['lang'] = languageFilter

		gqlRequest = [{
			'operationName': 'customEntitiesWithUsageQuery',
			'variables'    : variables,
			'query'        : customEntitiesWithUsageQuery
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)

		for entity in response['entities']:
			self._entitiesCache['cacheId'][entity['id']] = entity
			self._entitiesCache['cacheName'][entity['name']] = entity

		self._cacheInit = True

		if returnAllCacheIndexedBy:
			key = returnAllCacheIndexedBy[0].upper() + returnAllCacheIndexedBy[1:]
			return self._entitiesCache["cache" + key]

		if entityFilter:
			if entityFilterAttribute == 'id':
				return self._entitiesCache['cacheId'][entityFilter]
			elif entityFilterAttribute == 'name':
				return self._entitiesCache['cacheName'][entityFilter]

		return response['entities']


	def listEntitiesByUserEmailAndIntentId(self, userEmail: str, intentId: str, languageFilter: str = None, indexedBy: str = None, fromCache: bool = False) -> typing.Iterable:
		if fromCache and self._cacheInit:
			entities = self._entitiesCache['cacheId'].values()
		else:
			entities = self.listEntitiesByUserEmail(userEmail=userEmail, languageFilter=languageFilter)

		intentEntities = list()
		indexedIntentEntities = dict()

		for entity in entities:
			if entity['usedIn']:
				for intentMeta in entity['usedIn']:
					if intentMeta['intentId'] == intentId:
						if indexedBy:
							indexedIntentEntities[entity[indexedBy]] = entity
						else:
							intentEntities.append(entity)

		if indexedBy:
			return indexedIntentEntities

		return intentEntities


	def listEntityValuesByEntityId(self, entityId: str) -> str:
		variables = {'entityId': entityId}

		gqlRequest = [{
			'operationName': 'FullCustomEntityQuery',
			'variables'    : variables,
			'query'        : fullCustomEntityQuery
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)

		return response['entity']['data']


	@staticmethod
	def formatSlotValues(slotValues: list) -> list:
		formattedSlotValues = list()

		for slotValue in slotValues:
			formattedSlotValues.append({
				'value'        : slotValue['value'],
				'synonyms'     : slotValue.get('synonyms', list()),
				'fromWikilists': None
			})

		return formattedSlotValues


	# noinspection PyUnusedLocal
	def create(self, name: str, language: str, matchingStrictness: int = 1, automaticallyExtensible: bool = False, useSynonyms: bool = True, slotValues: list = None) -> str:
		"""
		Warning: mind the language parameter if the assistant language is EN, entity must set language to EN
		no error will be shown and the entity won't be created
		"""
		if not slotValues:
			slotValues = list()

		# Slot values exemple:
		# [ {'value': 'room'}, {'value': 'house', 'synonyms': ['entire house']} ]
		formattedSlotValues = self.formatSlotValues(slotValues)

		gqlRequest = [{
			'operationName': 'createIntentEntity',
			'variables'    : {
				'input': {
					'author'                 : self._ctx.userEmail,
					'automaticallyExtensible': automaticallyExtensible,
					'data'                   : formattedSlotValues,
					'language'               : language,
					'name'                   : name,
					'private'                : True,
					'useSynonyms'            : useSynonyms
				}
			},
			'query'        : createIntentEntity
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)
		createdEntityId = response['createIntentEntity']['id']

		return createdEntityId


	def edit(self, entityId: str, name: str = None, automaticallyExtensible: bool = False, matchingStrictness: int = None, useSynonyms: bool = False, slotValues: list = None):
		"""
		Slot values must include old values AND the new one
		"""
		if not slotValues:
			slotValues = list()

		inputt = dict()

		if name: inputt['name'] = name
		if automaticallyExtensible: inputt['automaticallyExtensible'] = automaticallyExtensible
		if matchingStrictness: inputt['matchingStrictness'] = matchingStrictness
		if useSynonyms: inputt['useSynonyms'] = useSynonyms

		if slotValues:
			inputt['data'] = self.formatSlotValues(slotValues)

		gqlRequest = [{
			'operationName': 'patchIntentEntity',
			'variables'    : {
				'intentEntityId': entityId,
				'input'         : inputt
			},
			'query'        : patchIntentEntity
		}]
		self._ctx.postGQLBrowserly(gqlRequest, rawResponse=True)


	# noinspection PyUnusedLocal
	def delete(self, entityId: str, language: str = None):
		gqlRequest = [{
			'operationName': 'deleteIntentEntity',
			'variables'    : {
				'email': self._ctx.userEmail,
				'id'   : entityId
				# 'lang': language # seems it's not mandatory
			},
			'query'        : deleteIntentEntity
		}]
		self._ctx.postGQLBrowserly(gqlRequest, rawResponse=True)
