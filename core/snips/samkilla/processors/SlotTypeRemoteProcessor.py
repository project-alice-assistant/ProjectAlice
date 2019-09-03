import sys
import traceback

import hashlib

from core.snips import SamkillaManager


class SlotTypeRemoteProcessor:

	def __init__(self, ctx: SamkillaManager, slotType: dict, slotLanguage: str, assistantId: str):
		self._ctx = ctx
		self._slotType = slotType
		self._assistantId = assistantId
		self._slotTypeLanguage = slotLanguage
		self._syncState = None
		self._createdInstances = {'entities': list()}


	def createNewSavedSlotType(self) -> dict:
		return {
			'name': self._slotType['name']
		}


	def slotTypeValuesToHash(self, entityId: str = '') -> str:
		slotType = self._slotType

		hashSum = '{}{}{}{}'.format(
			str(slotType['name']),
			str(slotType['matchingStrictness']),
			str(slotType['automaticallyExtensible']),
			str(slotType['useSynonyms'])
		)

		for valueObject in slotType['values']:
			hashSum += str(valueObject['value'])
			if 'synonyms' in valueObject:
				for synonym in valueObject['synonyms']:
					hashSum += str(synonym)

		hashSum += entityId

		return hashlib.sha512(hashSum.encode('utf-8')).hexdigest()


	def syncedSlotTypeExists(self) -> bool:
		return 'hash' in self._syncState and 'entityId' in self._syncState


	def syncSlotType(self, hashComputationOnly = False) -> dict:
		slotType = self._slotType

		oldInstanceExists = self.syncedSlotTypeExists()
		oldHash = self._syncState['hash'] if oldInstanceExists else ''
		entityId = self._syncState['entityId'] if oldInstanceExists else ''
		curHash = self.slotTypeValuesToHash(entityId=entityId)
		changes = False

		if hashComputationOnly or (oldInstanceExists and oldHash == curHash):
			self._ctx.log('[Sync] Entity|SlotType model {} = {} has no changes'.format(entityId, slotType['name']))
		elif oldInstanceExists:
			changes = True
			self._ctx.log('[Sync] Entity|SlotType model {} = {} has been edited'.format(entityId, slotType['name']))
			self._ctx.entity.edit(
				entityId,
				name=slotType['name'],
				matchingStrictness=slotType['matchingStrictness'],
				automaticallyExtensible=slotType['automaticallyExtensible'],
				useSynonyms=slotType['useSynonyms'],
				slotValues=slotType['values']
			)
		else:
			changes = True
			entityId = self._ctx.entity.create(
				language=self._slotTypeLanguage,
				name=slotType['name'],
				matchingStrictness=slotType['matchingStrictness'],
				automaticallyExtensible=slotType['automaticallyExtensible'],
				useSynonyms=slotType['useSynonyms'],
				slotValues=slotType['values']
			)
			self._ctx.log('[Sync] Entity|SlotType model {} = {} has been created'.format(entityId, slotType['name']))
			self._createdInstances['entities'].append({'id': entityId})
			curHash = self.slotTypeValuesToHash(entityId=entityId)

		return {'entityId': entityId, 'hash': curHash, 'changes': changes}


	def syncSlotTypesOnAssistantSafely(self, slotTypeSyncState: str = None, hashComputationOnly: bool = False):
		try:
			return self.syncSlotTypesOnAssistant(slotTypeSyncState=slotTypeSyncState, hashComputationOnly=hashComputationOnly)
		except:
			e = sys.exc_info()[0]
			self._ctx.log('[Safe] Handle error gracefully')
			self._ctx.log(e)
			self._ctx.log(traceback.format_exc())
			sys.exit(-1)


	def syncSlotTypesOnAssistant(self, slotTypeSyncState: str = None, hashComputationOnly: bool = False) -> tuple:
		self._syncState = slotTypeSyncState or self.createNewSavedSlotType()

		slotTypeMatching = self.syncSlotType(hashComputationOnly)
		self._syncState['hash'] = slotTypeMatching['hash']
		self._syncState['entityId'] = slotTypeMatching['entityId']

		return self._syncState, slotTypeMatching['changes']


	def cleanCreatedInstances(self):
		self._ctx.log('[Cleanup] Deleting {} entities'.format(len(self._createdInstances['entities'])))
		for entity in self._createdInstances['entities']:
			self._ctx.entity.delete(entityId=entity['id'])
		self._createdInstances['entities'] = list()
