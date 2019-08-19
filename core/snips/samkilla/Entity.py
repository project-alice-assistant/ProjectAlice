# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.entities.createIntentEntity import createIntentEntity
from core.snips.samkilla.gql.entities.deleteIntentEntity import deleteIntentEntity
from core.snips.samkilla.gql.entities.patchIntentEntity import patchIntentEntity
from core.snips.samkilla.gql.entities.queries import customEntitiesWithUsageQuery
from core.snips.samkilla.gql.entities.queries import fullCustomEntityQuery


class Entity():

	def __init__(self, ctx):
		self._ctx = ctx
		self._cacheInit = False
		self._entitiesCache = {"cacheId": {}, "cacheName": {}}

	def getEntityByUserEmailAndEntityName(self, userEmail, entityName):
		entity = None

		if entityName in self._entitiesCache["cacheName"]:
			entity = self._entitiesCache["cacheName"][entityName]
		else:
			entity = self.listEntitiesByUserEmail(userEmail, entityFilter=entityName, entityFilterAttribute="name")

		return entity

	def getEntityByUserEmailAndEntityId(self, userEmail, entityId):
		entity = None

		if entityId in self._entitiesCache["cacheId"]:
			entity = self._entitiesCache["cacheId"][entityId]
		else:
			entity = self.listEntitiesByUserEmail(userEmail, entityFilter=entityId)

		return entity

	def listEntitiesByUserEmail(self, userEmail, entityFilter=None, languageFilter=None, entityFilterAttribute="id", returnAllCacheIndexedBy=None):
		variables = {"email": userEmail}

		if languageFilter:
			variables["lang"] = languageFilter

		gqlRequest = [{
			"operationName": "customEntitiesWithUsageQuery",
			"variables": variables,
			"query": customEntitiesWithUsageQuery
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)

		for entity in response['entities']:
			self._entitiesCache["cacheId"][entity["id"]] = entity
			self._entitiesCache["cacheName"][entity["name"]] = entity

		self._cacheInit = True

		if returnAllCacheIndexedBy:
			key = returnAllCacheIndexedBy[0].upper() + returnAllCacheIndexedBy[1:]
			return self._entitiesCache["cache" + key]

		if entityFilter:
			if entityFilterAttribute == "id":
				return self._entitiesCache["cacheId"][entityFilter]
			elif entityFilterAttribute == "name":
				return self._entitiesCache["cacheName"][entityFilter]

		return response['entities']

	def listEntitiesByUserEmailAndIntentId(self, userEmail, intentId, languageFilter=None, indexedBy=None, fromCache=False):
		entities = list()

		if fromCache and self._cacheInit:
			entities = self._entitiesCache["cacheId"].values()
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

	def listEntityValuesByEntityId(self, entityId):
		variables = { "entityId": entityId }

		gqlRequest = [{
			"operationName": "FullCustomEntityQuery",
			"variables": variables,
			"query": fullCustomEntityQuery
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)

		return response['entity']['data']





	def formatSlotValues(self, slotValues):
		formattedSlotValues = list()

		for slotValue in slotValues:
			formattedSlotValues.append({
				"value": slotValue["value"],
				"synonyms": slotValue["synonyms"] if "synonyms" in slotValue else [],
				"fromWikilists": None
			})

		return formattedSlotValues

	# Warning: mind the language parameter if the assistant language is EN, entity must set language to EN
	# no error will be shown and the entity won't be created
	def create(self, name, language, matchingStrictness=1, automaticallyExtensible=False, useSynonyms=True, slotValues=[]):

		# Slot values exemple:
		#[ {"value": "room"}, {"value": "house", "synonyms": ["entire house"]} ]
		formattedSlotValues = self.formatSlotValues(slotValues)

		gqlRequest = [{
			"operationName": "createIntentEntity",
			"variables": {
				"input": {
					"author": self._ctx._userEmail,
					"automaticallyExtensible": automaticallyExtensible,
					"data": formattedSlotValues,
					"language": language,
					"name": name,
					"private": True,
					"useSynonyms": useSynonyms
				}
			},
			"query": createIntentEntity
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)
		createdEntityId = response["createIntentEntity"]["id"]

		return createdEntityId


	# Slot values must include old values AND the new ones
	def edit(self, entityId, name=None, automaticallyExtensible=None, matchingStrictness=None, useSynonyms=None, slotValues=None):
		input = dict()

		if name: input['name'] = name
		if automaticallyExtensible: input['automaticallyExtensible'] = automaticallyExtensible
		if matchingStrictness: input['matchingStrictness'] = matchingStrictness
		if useSynonyms: input['useSynonyms'] = useSynonyms

		if slotValues:
			input['data'] = self.formatSlotValues(slotValues)

		gqlRequest = [{
			"operationName": "patchIntentEntity",
			"variables": {
				"intentEntityId": entityId,
				"input": input
			},
			"query": patchIntentEntity
		}]
		self._ctx.postGQLBrowserly(gqlRequest, rawResponse=True)


	def delete(self, entityId, language=None):
		gqlRequest = [{
			"operationName": "deleteIntentEntity",
			"variables": {
				"email": self._ctx._userEmail,
				"id": entityId
				# "lang": language # seems it's not mandatory
			},
			"query": deleteIntentEntity
		}]
		self._ctx.postGQLBrowserly(gqlRequest, rawResponse=True)
