# -*- coding: utf-8 -*-

import sys
import traceback

import hashlib

from core.snips.samkilla.exceptions.IntentError import IntentError


class IntentRemoteProcessor():

	def __init__(self, ctx, intent, intentLanguage, assistantId):
		self._ctx = ctx
		self._intent = intent
		self._assistantId = assistantId
		self._intentLanguage = intentLanguage
		self._syncState = None
		self._createdInstances = {'intents': list()}

	def createNewSavedIntent(self):
		return {
			'name': self._intent['name']
		}

	def intentValuesToHash(self, typeEntityMatching, intentId='', skillId=''):
		intent = self._intent
		
		hashSum = '{}{}{}'.format(
			str(intent['name']),
			str(intent['description']),
			str(intent['enabledByDefault'])
		)

		for utteranceText in intent['utterances']:
			hashSum += str(utteranceText)

		for slotHole in intent['slots']:
			hashSum += str(slotHole['name'])
			hashSum += str(slotHole['description'])
			hashSum += str(slotHole['required'])
			hashSum += str(slotHole['type'])
			hashSum += str(slotHole['missingQuestion'])

			if slotHole['type'] in typeEntityMatching:
				hashSum += typeEntityMatching[slotHole['type']]['entityId']

		hashSum += intentId + '-' + skillId

		return hashlib.sha512(hashSum.encode('utf-8')).hexdigest()
		
	def doSyncedIntentExists(self):
		return "hash" in self._syncState and "intentId" in self._syncState

	def syncIntent(self, typeEntityMatching, skillId, hashComputationOnly=False):
		intent = self._intent

		oldInstanceExists = self.doSyncedIntentExists()
		oldHash = self._syncState['hash'] if oldInstanceExists else ''
		intentId = self._syncState['intentId'] if oldInstanceExists else ''
		curHash = self.intentValuesToHash(typeEntityMatching=typeEntityMatching, intentId=intentId, skillId=skillId)
		changes = False

		fullIntentName = intent['name']

		if hashComputationOnly or (oldInstanceExists and oldHash == curHash):
			self._ctx.log("[Sync] Intent model {} = {} has no changes".format(intentId, fullIntentName))
		elif oldInstanceExists:
			changes = True
			self._ctx.log("[Sync] Intent model {} = {} has been edited".format(intentId, fullIntentName))
			self._ctx.Intent.edit(
				userId=self._ctx.userId,
				intentId=intentId,
				name=fullIntentName,
				description=intent['description'],
				enabledByDefault=intent['enabledByDefault'],
				typeEntityMatching=typeEntityMatching,
				slotsDefinition=intent['slots'],
				utterancesDefinition=intent['utterances'],
				attachToSkill=True,
				skillId=skillId,
				language=self._intentLanguage
			)
		else:
			changes = True
			intentId = self._ctx.Intent.create(
				userId=self._ctx.userId,
				skillId=skillId,
				name=fullIntentName,
				description=intent['description'],
				language=self._intentLanguage,
				attachToSkill=True,
				enabledByDefault=intent['enabledByDefault'],
				typeEntityMatching=typeEntityMatching,
				slotsDefinition=intent['slots'],
				utterancesDefinition=intent['utterances']
			)
			self._ctx.log("[Sync] Intent model {} = {} has been created".format(intentId, fullIntentName))
			self._createdInstances['intents'].append({'id': intentId})
			curHash = self.intentValuesToHash(typeEntityMatching=typeEntityMatching, intentId=intentId, skillId=skillId)

		return {'intentId': intentId, 'hash': curHash, 'changes': changes}
	
	
	def syncIntentsOnAssistantSafely(self, typeEntityMatching, skillId, intentSyncState=None, hashComputationOnly=False):
		try:
			return self.syncIntentsOnAssistant(typeEntityMatching=typeEntityMatching, skillId=skillId, intentSyncState=intentSyncState, hashComputationOnly=hashComputationOnly)
		except IntentError as ie:
			self._ctx.log("[Safe] Handle error gracefully")
			self._ctx.log(ie.message)

			# Deprecated
			# self.cleanCreatedInstances()
		except Exception as e:
			e = sys.exc_info()[0]
			self._ctx.log("[Safe] Handle error gracefully")
			self._ctx.log(e)
			self._ctx.log(traceback.format_exc())
			sys.exit(-1)

	def syncIntentsOnAssistant(self, typeEntityMatching, skillId, intentSyncState=None, hashComputationOnly=False):
		self._syncState = self.createNewSavedIntent() if intentSyncState is None else intentSyncState

		intentMatching = self.syncIntent(typeEntityMatching, skillId, hashComputationOnly)
		self._syncState['hash'] = intentMatching['hash']
		self._syncState['intentId'] = intentMatching['intentId']

		return self._syncState, intentMatching['changes']


	def cleanCreatedInstances(self):
		self._ctx.log("[Cleanup] Deleting {} intents".format(len(self._createdInstances['intents'])))
		for intent in self._createdInstances['intents']:
			self._ctx.Entity.delete(intentId=intent['id'])
		self._createdInstances['intents'] = list()
