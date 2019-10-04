import requests
import time
import tempfile
from pathlib import Path

from core.snips import SamkillaManager
from core.snips.samkilla.gql.assistants.trainAssistant import trainAssistant
from core.snips.samkilla.gql.assistants.createAssistant import createAssistant
from core.snips.samkilla.gql.assistants.deleteAssistant import deleteAssistant
from core.snips.samkilla.gql.assistants.forkAssistantSkill import forkAssistantSkill
from core.snips.samkilla.gql.assistants.patchAssistant import patchAssistant
from core.snips.samkilla.gql.assistants.queries import allAssistantsQuery, assistantWithSkillsQuery, assistantTrainingStatusQuery


class Assistant:

	def __init__(self, ctx: SamkillaManager):
		self._ctx = ctx


	def create(self, title: str, language: str, platformType: str = 'raspberrypi', asrType: str = 'snips', hotwordId: str = 'hey_snips', rawResponse: bool = False) -> str:
		gqlRequest = [{
			'operationName': 'CreateAssistant',
			'variables'    : {
				'input': {
					'title'    : title,
					'platform' : {'type': platformType},
					'asr'      : {'type': asrType},
					'language' : language,
					'hotwordId': hotwordId
				}
			},
			'query'        : createAssistant
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)

		# Mandatory after a create action to update APOLLO_STATE, @TODO maybe update the state manually to improve performances ?
		self._ctx.reloadBrowserPage()

		if rawResponse: return response

		return response['createAssistant']['id']


	def edit(self, assistantId: str, title: str = None):
		inputt = dict()

		if title: inputt['title'] = title

		gqlRequest = [{
			'operationName': 'PatchAssistant',
			'variables'    : {
				'assistantId': assistantId,
				'input'      : inputt
			},
			'query'        : patchAssistant
		}]
		self._ctx.postGQLBrowserly(gqlRequest)


	def delete(self, assistantId: str) -> requests.Response:
		gqlRequest = [{
			'operationName': 'DeleteAssistant',
			'variables'    : {'assistantId': assistantId},
			'query'        : deleteAssistant
		}]
		return self._ctx.postGQLBrowserly(gqlRequest)


	def list(self, rawResponse: bool = False, parseWithAttribute: str = 'id') -> list:
		gqlRequest = [{
			'operationName': 'AssistantsQuery',
			'variables'    : dict(),
			'query'        : allAssistantsQuery
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)
		if rawResponse: return response

		if parseWithAttribute and parseWithAttribute != '':
			return [assistantItem[parseWithAttribute] for assistantItem in response['assistants']]

		return response['assistants']


	def getTitleById(self, assistantId: str) -> str:
		for assistantItem in self.list(parseWithAttribute=''):
			if assistantItem['id'] == assistantId:
				return assistantItem['title']

		return ''


	def exists(self, assistantId: str) -> bool:
		for listItemAssistantId in self.list():
			if listItemAssistantId == assistantId:
				return True

		return False


	def extractSkillIdentifiersLegacy(self, assistantId: str) -> list:
		skills = self._ctx.getBrowser().execute_script(f"return window.__APOLLO_STATE__['Assistant:{assistantId}']['skills']")

		return [skill['id'].replace('Skill:', '') for skill in skills]


	def extractSkillIdentifiers(self, assistantId: str) -> list:
		gqlRequest = [{
			'operationName': 'AssistantWithSkillsQuery',
			'variables': {'assistantId': assistantId},
			'query': assistantWithSkillsQuery
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)

		return [skill['id'] for skill in response['assistant']['skills']]


	def forkAssistantSkill(self, assistantId: str, sourceSkillId: str) -> str:
		gqlRequest = [{
			'operationName': 'forkAssistantSkill',
			'variables'    : {'assistantId': assistantId, 'skillId': sourceSkillId},
			'query'        : forkAssistantSkill
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)

		return response['forkAssistantSkill']['copiedBundleId']

	def trainAssistant(self, assistantId: str) -> bool:
		gqlRequest = [{
			'operationName': 'TrainAssistantV2',
			'variables': {'assistantId': assistantId},
			'query': trainAssistant
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)

		return True

	def trainingStatusAssistantReady(self, assistantId: str) -> bool:
		gqlRequest = [{
			'operationName': 'AssistantTrainingStatusQuery',
			'variables': {'assistantId': assistantId},
			'query': assistantTrainingStatusQuery
		}]
		response = self._ctx.postGQLBrowserly(gqlRequest)

		asrProgress = response['assistant']['training']['asrStatus']['inProgress']
		asrResult = response['assistant']['training']['asrStatus']['trainingResult']
		asrNeedTraining = response['assistant']['training']['asrStatus']['needTraining']

		nluProgress = response['assistant']['training']['nluStatus']['inProgress']
		nluResult = response['assistant']['training']['nluStatus']['trainingResult']
		nluNeedTraining = response['assistant']['training']['nluStatus']['needTraining']

		if not asrProgress and not asrNeedTraining and asrResult == 'ok' \
			and not nluProgress and not nluNeedTraining and nluResult == 'ok':
			return True

		return False
