import hashlib
import sys
import traceback

from core.snips import SamkillaManager
from core.snips.samkilla.models.EnumSkillImageUrl import EnumSkillImageUrl as EnumSkillImageUrlClass

EnumSkillImageUrl = EnumSkillImageUrlClass()


class ModuleRemoteProcessor:

	def __init__(self, ctx: SamkillaManager, assistantId: str, module: dict, moduleName: str, moduleLanguage: str):
		self._ctx = ctx
		self._assistantId = assistantId
		self._module = module
		self._moduleName = moduleName
		self._moduleLanguage = moduleLanguage
		self._syncState = None
		self._createdInstances = {
			'skills': list()
		}


	def createNewSavedModule(self) -> dict:
		return {
			'skillId': None,
			'name'   : self._moduleName
		}


	@staticmethod
	def skillValuesToHash(icon: str, description: str, skillId: str = '') -> str:
		hashSum = f'{icon}{description}{skillId}'
		return hashlib.sha512(hashSum.encode('utf-8')).hexdigest()


	def syncedSkillExists(self) -> bool:
		return 'hash' in self._syncState and str(self._syncState['skillId']).startswith('skill_')


	def syncSkill(self, moduleDescription: str, moduleIcon: str, hashComputationOnly: bool = False):
		oldInstanceExists = self.syncedSkillExists()
		oldHash = self._syncState['hash'] if oldInstanceExists else ''
		skillId = self._syncState['skillId'] if oldInstanceExists else ''
		curHash = self.skillValuesToHash(icon=moduleIcon, description=moduleDescription, skillId=skillId)
		changes = False

		if hashComputationOnly or (oldInstanceExists and oldHash == curHash):
			self._ctx.log(f'Skill model {skillId} ({self._moduleName}) has no changes')
		elif oldInstanceExists:
			changes = True
			self._ctx.log(f'Skill model {skillId} ({self._moduleName}) has been edited')
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
			self._ctx.log(f'Skill model {skillId} ({self._moduleName}) has been created')
			self._createdInstances['skills'].append({'id': skillId, 'assistantId': self._assistantId})
			curHash = self.skillValuesToHash(icon=moduleIcon, description=moduleDescription, skillId=skillId)

		return {
			'skillId': skillId,
			'hash'   : curHash,
			'changes': changes
		}


	def syncModulesOnAssistantSafely(self, typeEntityMatching: dict, moduleSyncState: str = None, hashComputationOnly: bool = False):
		try:
			return self.syncModulesOnAssistant(typeEntityMatching=typeEntityMatching, moduleSyncState=moduleSyncState, hashComputationOnly=hashComputationOnly)
		except:
			e = sys.exc_info()[0]
			self._ctx.log('Handle error gracefully')
			self._ctx.log(e)
			self._ctx.log(traceback.format_exc())
			sys.exit(-1)


	# noinspection PyUnusedLocal
	def syncModulesOnAssistant(self, typeEntityMatching: dict = None, moduleSyncState: str = None, hashComputationOnly: bool = False) -> tuple:
		#TODO this appears wrong moduleSyncState is a str according to typing while self.createNewSavedModule() returns a dict
		# is is used as a dict aswell. Is the typing wrong?
		self._syncState = moduleSyncState or self.createNewSavedModule()

		skillData = self.syncSkill(self._module['description'], self._module['icon'], hashComputationOnly)
		self._syncState['skillId'] = skillData['skillId']
		self._syncState['hash'] = skillData['hash']
		self._syncState['name'] = self._moduleName

		return self._syncState, skillData['changes']


	def cleanCreatedInstances(self):
		self._ctx.log(f"[Cleanup] Deleting {len(self._createdInstances['skills'])} skills")
		for skill in self._createdInstances['skills']:
			self._ctx.skill.removeFromAssistant(assistantId=skill['assistantId'], skillId=skill['id'], deleteAfter=True)
		self._createdInstances['skills'] = list()
