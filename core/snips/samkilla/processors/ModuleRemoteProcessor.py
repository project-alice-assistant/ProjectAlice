import sys
import traceback

import hashlib

from core.snips.samkilla.models.EnumSkillImageUrl import EnumSkillImageUrl as EnumSkillImageUrlClass

EnumSkillImageUrl = EnumSkillImageUrlClass()


class ModuleRemoteProcessor:

	def __init__(self, ctx, assistantId, module, moduleName, moduleLanguage):
		self._ctx = ctx
		self._assistantId = assistantId
		self._module = module
		self._moduleName = moduleName
		self._moduleLanguage = moduleLanguage
		self._syncState = None
		self._createdInstances = {
			'skills': list()
		}


	def createNewSavedModule(self):
		return {
			'skillId': None,
			'name'   : self._moduleName
		}


	@staticmethod
	def skillValuesToHash(icon, description, skillId=''):
		hashSum = '{}{}{}'.format(icon, description, skillId)

		return hashlib.sha512(hashSum.encode('utf-8')).hexdigest()


	def doSyncedSkillExists(self):
		return 'hash' in self._syncState and \
			   str(self._syncState['skillId']).startswith("skill_")


	def syncSkill(self, moduleDescription, moduleIcon, hashComputationOnly=False):
		oldInstanceExists = self.doSyncedSkillExists()
		oldHash = self._syncState['hash'] if oldInstanceExists else ''
		skillId = self._syncState['skillId'] if oldInstanceExists else ''
		curHash = self.skillValuesToHash(icon=moduleIcon, description=moduleDescription, skillId=skillId)
		changes = False

		if hashComputationOnly or (oldInstanceExists and oldHash == curHash):
			self._ctx.log("[Sync] Skill model {} = {} has no changes".format(skillId, self._moduleName))
		elif oldInstanceExists:
			changes = True
			self._ctx.log("[Sync] Skill model {} = {} has been edited".format(skillId, self._moduleName))
			self._ctx.skill.edit(skillId, description=moduleDescription, imageKey=EnumSkillImageUrl.getResourceFileByAttr(moduleIcon))
		else:
			changes = True
			skillId = self._ctx.skill.create(
				assistantId=self._assistantId,
				name=self._moduleName,
				description=moduleDescription,
				language=self._moduleLanguage,
				imageKey=EnumSkillImageUrl.getResourceFileByAttr(moduleIcon),
				attachToAssistant=True
			)
			self._ctx.log("[Sync] Skill model {} = {} has been created".format(skillId, self._moduleName))
			self._createdInstances['skills'].append({"id": skillId, "assistantId": self._assistantId})
			curHash = self.skillValuesToHash(icon=moduleIcon, description=moduleDescription, skillId=skillId)

		return {
			'skillId': skillId,
			'hash'   : curHash,
			'changes': changes
		}


	def syncModulesOnAssistantSafely(self, typeEntityMatching, moduleSyncState=None, hashComputationOnly=False):
		try:
			return self.syncModulesOnAssistant(typeEntityMatching=typeEntityMatching, moduleSyncState=moduleSyncState, hashComputationOnly=hashComputationOnly)
		except:
			e = sys.exc_info()[0]
			self._ctx.log("[Safe] Handle error gracefully")
			self._ctx.log(e)
			self._ctx.log(traceback.format_exc())
			# Deprecated
			# self.cleanCreatedInstances()
			sys.exit(-1)


	# noinspection PyUnusedLocal
	def syncModulesOnAssistant(self, typeEntityMatching=None, moduleSyncState=None, hashComputationOnly=False):
		self._syncState = self.createNewSavedModule() if moduleSyncState is None else moduleSyncState

		skillData = self.syncSkill(self._module['description'], self._module['icon'], hashComputationOnly)
		self._syncState['skillId'] = skillData['skillId']
		self._syncState['hash'] = skillData['hash']
		self._syncState['name'] = self._moduleName

		return self._syncState, skillData['changes']


	def cleanCreatedInstances(self):
		self._ctx.log("[Cleanup] Deleting {} skills".format(len(self._createdInstances['skills'])))
		for skill in self._createdInstances['skills']:
			self._ctx.skill.removeFromAssistant(assistantId=skill['assistantId'], skillId=skill['id'], deleteAfter=True)
		self._createdInstances['skills'] = list()
