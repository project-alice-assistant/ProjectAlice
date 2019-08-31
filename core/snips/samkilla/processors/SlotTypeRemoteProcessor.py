# -*- coding: utf-8 -*-

import sys
import traceback

import hashlib


class SlotTypeRemoteProcessor():

	def __init__(self, ctx, slotType, slotLanguage, assistantId):
		self._ctx = ctx
		self._slotType = slotType
		self._assistantId = assistantId
		self._slotTypeLanguage = slotLanguage
		self._syncState = None
		self._createdInstances = {'entities': list()}

	def createNewSavedSlotType(self):
		return {
			'name': self._slotType['name']
		}

	def slotTypeValuesToHash(self, entityId=''):
		slotType = self._slotType
		
		hashSum = '{}{}{}{}'.format(
			str(slotType['name']),
			str(slotType['matchingStrictness']),
			str(slotType['automaticallyExtensible']),
			str(slotType['useSynonyms'])
		)

		for valueObject in slotType['values']:
			hashSum += str(valueObject['value'])
			if "synonyms" in valueObject:
				for synonym in valueObject['synonyms']:
					hashSum += str(synonym)

		hashSum += entityId

		return hashlib.sha512(hashSum.encode('utf-8')).hexdigest()
		
	def doSyncedSlotTypeExists(self):
		return "hash" in self._syncState and "entityId" in self._syncState

	def syncSlotType(self, hashComputationOnly=False):
		slotType = self._slotType

		oldInstanceExists = self.doSyncedSlotTypeExists()
		oldHash = self._syncState['hash'] if oldInstanceExists else ''
		entityId = self._syncState['entityId'] if oldInstanceExists else ''
		curHash = self.slotTypeValuesToHash(entityId=entityId)
		changes = False

		if hashComputationOnly or (oldInstanceExists and oldHash == curHash):
			self._ctx.log("[Sync] Entity|SlotType model {} = {} has no changes".format(entityId, slotType['name']))
		elif oldInstanceExists:
			changes = True
			self._ctx.log("[Sync] Entity|SlotType model {} = {} has been edited".format(entityId, slotType['name']))
			self._ctx.Entity.edit(
				entityId,
				name=slotType['name'],
				matchingStrictness=slotType['matchingStrictness'],
				automaticallyExtensible=slotType['automaticallyExtensible'],
				useSynonyms=slotType['useSynonyms'],
				slotValues=slotType['values']
			)
		else:
			changes = True
			entityId = self._ctx.Entity.create(
				language=self._slotTypeLanguage,
				name=slotType['name'],
				matchingStrictness=slotType['matchingStrictness'],
				automaticallyExtensible=slotType['automaticallyExtensible'],
				useSynonyms=slotType['useSynonyms'],
				slotValues=slotType['values']
			)
			self._ctx.log("[Sync] Entity|SlotType model {} = {} has been created".format(entityId, slotType['name']))
			self._createdInstances['entities'].append({"id": entityId})
			curHash = self.slotTypeValuesToHash(entityId=entityId)

		return {"entityId": entityId, "hash": curHash, "changes": changes}
	
	
	def syncSlotTypesOnAssistantSafely(self, slotTypeSyncState=None, hashComputationOnly=False):
		try:
			return self.syncSlotTypesOnAssistant(slotTypeSyncState=slotTypeSyncState, hashComputationOnly=hashComputationOnly)
		except:
			e = sys.exc_info()[0]
			self._ctx.log('[Safe] Handle error gracefully')
			self._ctx.log(e)
			self._ctx.log(traceback.format_exc())
			# Deprecated
			# self.cleanCreatedInstances()
			sys.exit(-1)

	def syncSlotTypesOnAssistant(self, slotTypeSyncState=None, hashComputationOnly=False):
		self._syncState = self.createNewSavedSlotType() if slotTypeSyncState is None else slotTypeSyncState

		slotTypeMatching = self.syncSlotType(hashComputationOnly)
		self._syncState['hash'] = slotTypeMatching['hash']
		self._syncState['entityId'] = slotTypeMatching['entityId']

		return self._syncState, slotTypeMatching['changes']


	def cleanCreatedInstances(self):
		self._ctx.log("[Cleanup] Deleting {} entities".format(len(self._createdInstances['entities'])))
		for entity in self._createdInstances['entities']:
			self._ctx.Entity.delete(entityId=entity['id'])
		self._createdInstances['entities'] = list()
