# -*- coding: utf-8 -*-

from core.snips.samkilla.gql.assistants.createAssistant import createAssistant
from core.snips.samkilla.gql.assistants.deleteAssistant import deleteAssistant
from core.snips.samkilla.gql.assistants.forkAssistantSkill import forkAssistantSkill
from core.snips.samkilla.gql.assistants.patchAssistant import patchAssistant
from core.snips.samkilla.gql.assistants.queries import allAssistantsQuery


class Assistant():

	def __init__(self, ctx):
		self._ctx = ctx

	def create(self, title, language, platformType='raspberrypi', asrType='snips', hotwordId='hey_snips', rawResponse=False):
		gqlRequest = [{
			'operationName': 'CreateAssistant',
			'variables': {
				'input': {
					'title': title,
					'platform': {'type': platformType},
					'asr': {'type': asrType},
					'language': language,
					'hotwordId': hotwordId
				}
			},
			'query': createAssistant
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)

		# Mandatory after a create action to update APOLLO_STATE, @TODO maybe update the state manually to improve performances ?
		self._ctx.reloadBrowserPage()

		if rawResponse: return response

		return response['createAssistant']['id']


	def edit(self, assistantId, title=None):
		input = dict()

		if title: input['title'] = title

		gqlRequest = [{
			'operationName': 'PatchAssistant',
			'variables': {
				'assistantId': assistantId,
				'input': input
			},
			'query': patchAssistant
		}]
		self._ctx.postGQLBrowserly(gqlRequest)


	def delete(self, assistantId, rawResponse=False):
		gqlRequest = [{
			'operationName': 'DeleteAssistant',
			'variables':  {'assistantId': assistantId},
			'query': deleteAssistant
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)
		if rawResponse: return response

		return response


	def list(self, rawResponse=False, parseWithAttribute='id'):
		gqlRequest = [{
			'operationName': 'AssistantsQuery',
			'variables': dict(),
			'query': allAssistantsQuery
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)
		if rawResponse: return response

		if parseWithAttribute and parseWithAttribute != '':
			return [assistantItem[parseWithAttribute] for assistantItem in response['assistants']]

		return response['assistants']

	def getTitleById(self, assistantId):
		for assistantItem in self.list(parseWithAttribute=''):
			if assistantItem['id'] == assistantId:
				return assistantItem['title']

		return ""

	def exists(self, assistantId):
		for listItemAssistantId in self.list():
			if listItemAssistantId == assistantId:
				return True

		return False

	def extractSkillIdentifiers(self, assistantId):
		skills = self._ctx.getBrowser().execute_script("return window.__APOLLO_STATE__['Assistant:{}']['skills']".format(assistantId))

		return [skill['id'].replace('Skill:', '') for skill in skills]


	def forkAssistantSkill(self, assistantId, sourceSkillId):
		gqlRequest = [{
			'operationName': 'forkAssistantSkill',
			'variables': {'assistantId': assistantId, 'skillId': sourceSkillId},
			'query': forkAssistantSkill
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)

		return response['forkAssistantSkill']['copiedBundleId']
