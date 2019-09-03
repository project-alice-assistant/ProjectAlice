import typing

from core.snips import SamkillaManager
from core.ProjectAliceExceptions import HttpError
from core.snips.samkilla.gql.assistants.patchAssistantSkills import patchAssistantSkills
from core.snips.samkilla.gql.skills.createSkill import createSkill
from core.snips.samkilla.gql.skills.deleteSkill import deleteSkill
from core.snips.samkilla.gql.skills.editSkill import editSkill
from core.snips.samkilla.gql.skills.forkSkillIntent import forkSkillIntent
from core.snips.samkilla.gql.skills.queries import skillsWithUsageQuery
from core.snips.samkilla.models.EnumSkillImageUrl import EnumSkillImageUrl as EnumSkillImageUrlClass

EnumSkillImageUrl = EnumSkillImageUrlClass()

import re

intent_regex = re.compile(r'intent_([a-zA-Z0-9]+)')


class Skill:

	def __init__(self, ctx: SamkillaManager):
		self._ctx = ctx
		self._cacheInit = False
		self._skillsCache = {'cacheId': dict(), 'cacheName': dict()}


	def getSkillByUserIdAndSkillName(self, userId: str, skillName: str):
		return self._skillsCache['cachename'].get(skillName, self.listSkillsByUserId(userId, skillFilter=skillName, skillFilterAttribute='name'))


	def getSkillByUserIdAndSkillId(self, userId: str, skillId: str):
		return self._skillsCache['cacheId'].get(skillId, self.listSkillsByUserId(userId, skillFilter=skillId))


	def listSkillsByUserId(self, userId: str, skillFilter: str = None, skillFilterAttribute: str = 'id', languageFilter: str = None,
						   intentId: str = None, returnAllCacheIndexedBy: str = None, page: int = 1, totalSkills: int = None) -> typing.Iterable:
		if not totalSkills:
			totalSkills = list()

		variables = {
			'userId': userId,
			'offset': (page - 1) * 50,
			'limit' : 50,
			'sort'  : 'lastUpdated'
		}

		# 50 is the max limit server side
		if languageFilter: variables['lang'] = languageFilter
		if intentId: variables['intentId'] = intentId

		gqlRequest = [{
			'operationName': 'SkillsWithUsageQuery',
			'variables'    : variables,
			'query'        : skillsWithUsageQuery
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)

		for skill in response['skills']['skills']:
			self._skillsCache['cacheId'][skill['id']] = skill
			self._skillsCache['cacheName'][skill['name']] = skill
			totalSkills.append(skill)

		if (page - 1) * 50 < response['skills']['pagination']['total']:
			return self.listSkillsByUserId(userId, skillFilter, skillFilterAttribute, languageFilter, intentId, returnAllCacheIndexedBy, page=page + 1, totalSkills=totalSkills)

		self._cacheInit = True

		if returnAllCacheIndexedBy:
			key = returnAllCacheIndexedBy[0].upper() + returnAllCacheIndexedBy[1:]
			return self._skillsCache['cache' + key]

		if skillFilter:
			if skillFilterAttribute == 'id':
				return self._skillsCache['cacheId'][skillFilter]
			elif skillFilterAttribute == 'name':
				return self._skillsCache['cacheName'][skillFilter]

		return totalSkills


	def listSkillsByUserIdAndAssistantId(self, userId: str, assistantId: str, languageFilter: str = None, indexedBy: str = None, fromCache: bool = False) -> typing.Iterable:
		if fromCache and self._cacheInit:
			skills = self._skillsCache['cacheId'].values()
		else:
			skills = self.listSkillsByUserId(userId=userId, languageFilter=languageFilter)

		assistantSkills = list()
		indexedAssistantSkills = dict()

		for skill in skills:
			if skill['usedIn']:
				for assistantMeta in skill['usedIn']:
					if assistantMeta['assistantId'] == assistantId:
						if indexedBy:
							indexedAssistantSkills[skill[indexedBy]] = skill
						else:
							assistantSkills.append(skill)

		if indexedBy:
			return indexedAssistantSkills

		return assistantSkills


	def create(self, assistantId: str, language: str, name: str = 'Untitled', description: str = '', imageKey: str = EnumSkillImageUrl.default,
			   attachToAssistant: bool = True, intents: typing.Iterable = None) -> str:
		"""
		Warning: mind the language parameter if the assistant language is EN, skill must set language to EN
		no error will be shown and the skill won't be created
		"""
		if not intents:
			intents = list()

		gqlRequest = [{
			'operationName': 'createSkill',
			'variables'    : {
				'input': {
					'description': description,
					'imageUrl'   : EnumSkillImageUrl.getImageUrl(self._ctx.ROOT_URL, imageKey),
					'intents'    : intents,
					'language'   : language,
					'name'       : name,
					'private'    : True
				}
			},
			'query'        : createSkill
		}]
		resp = self._ctx.postGQLBrowserly(gqlRequest)

		createdSkillId = resp['createSkill']['id']

		if attachToAssistant:
			self.attachToAssistant(assistantId=assistantId, skillId=createdSkillId)

		return createdSkillId


	def attachToAssistant(self, assistantId: str, skillId: str):
		existingSkills = self._ctx.assistant.extractSkillIdentifiers(assistantId=assistantId)
		variablesSkills = [{'id': skillId, 'parameters': None}]

		for existingSkillId in existingSkills:
			variablesSkills.append({'id': existingSkillId, 'parameters': None})

		gqlRequest = [{
			'operationName': 'PatchAssistantSkills',
			'variables'    : {
				'assistantId': assistantId,
				'input'      : {
					'skills': variablesSkills
				}
			},
			'query'        : patchAssistantSkills
		}]
		self._ctx.postGQLBrowserly(gqlRequest, rawResponse=True)

		# Mandatory after a create action to update APOLLO_STATE, @TODO maybe update the state manually to improve performances ?
		self._ctx.reloadBrowserPage()


	def edit(self, skillId: str, name: str = None, description: str = None, imageKey: str = None):
		inputt = {'id': skillId}

		if name: inputt['name'] = name
		if description: inputt['description'] = description
		if imageKey: inputt['imageUrl'] = EnumSkillImageUrl.getImageUrl(self._ctx.ROOT_URL, imageKey)

		gqlRequest = [{
			'operationName': 'editSkill',
			'variables'    : {
				'input': inputt
			},
			'query'        : editSkill
		}]
		self._ctx.postGQLBrowserly(gqlRequest, rawResponse=True)


	def delete(self, skillId: str, reload: bool = True):
		gqlRequest = [{
			'operationName': 'deleteSkill',
			'variables'    : {'skillId': skillId},
			'query'        : deleteSkill
		}]
		self._ctx.postGQLBrowserly(gqlRequest)

		if reload:
			# Mandatory after a create action to update APOLLO_STATE, @TODO maybe update the state manually to improve performances ?
			self._ctx.reloadBrowserPage()


	def removeFromAssistant(self, assistantId: str, skillId: str, deleteAfter: str = False):
		existingSkills = self._ctx.assistant.extractSkillIdentifiers(assistantId=assistantId)
		variablesSkills = list()

		for existingSkillId in existingSkills:
			if existingSkillId != skillId:
				variablesSkills.append({'id': existingSkillId, 'parameters': None})

		gqlRequest = [{
			'operationName': 'PatchAssistantSkills',
			'variables'    : {
				'assistantId': assistantId,
				'input'      : {
					'skills': variablesSkills
				}
			},
			'query'        : patchAssistantSkills
		}]
		self._ctx.postGQLBrowserly(gqlRequest, rawResponse=True)

		if deleteAfter:
			self.delete(skillId=skillId, reload=False)

		# Mandatory after a create action to update APOLLO_STATE, @TODO maybe update the state manually to improve performances ?
		self._ctx.reloadBrowserPage()


	def forkSkillIntent(self, skillId: str, sourceIntentId: str, userId: str, newIntentName: str = None) -> str:
		gqlRequest = [{
			'operationName': 'forkSkillIntent',
			'variables'    : {'skillId': skillId, 'intentId': sourceIntentId, 'newIntentName': newIntentName},
			'query'        : forkSkillIntent
		}]

		try:
			response = self._ctx.postGQLBrowserly(gqlRequest)
		except HttpError as he:
			items = intent_regex.findall(he.message)

			if len(items) == 1:
				oldIntentId = "intent_{}".format(items[0])
				intentDuplicate = self._ctx.intent.getIntentByUserIdAndIntentId(userId, oldIntentId)
				self._ctx.log("Duplicate intent with id,name {},{}".format(oldIntentId, intentDuplicate['name']))

				if intentDuplicate:
					if 'usedIn' in intentDuplicate and intentDuplicate['usedIn']:
						for skillItem in intentDuplicate['usedIn']:
							self._ctx.intent.removeFromSkill(intentId=intentDuplicate['id'], skillId=skillItem['skillId'], userId=userId, deleteAfter=False)
					self._ctx.intent.delete(intentId=intentDuplicate['id'])
					return self.forkSkillIntent(skillId, sourceIntentId, userId, newIntentName)

			raise he

		return response['forkSkillIntent']['intentCopied']['id']
