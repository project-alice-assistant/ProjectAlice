import hashlib
import sys
import traceback

from core.snips import SamkillaManager
from core.snips.samkilla.models.EnumSkillImageUrl import EnumSkillImageUrl as EnumSkillImageUrlClass

EnumSkillImageUrl = EnumSkillImageUrlClass()


class SkillRemoteProcessor:

	def __init__(self, ctx: SamkillaManager, assistantId: str, skill: dict, skillName: str, skillLanguage: str):
		self._ctx = ctx
		self._assistantId = assistantId
		self._skill = skill
		self._skillName = skillName
		self._skillLanguage = skillLanguage
		self._syncState = None
		self._createdInstances = {
			'skills': list()
		}


	def createNewSavedSkill(self) -> dict:
		return {
			'skillId': None,
			'name': self._skillName
		}


	@staticmethod
	def skillValuesToHash(icon: str, description: str, skillId: str = '') -> str:
		hashSum = f'{icon}{description}{skillId}'
		return hashlib.sha512(hashSum.encode('utf-8')).hexdigest()


	def syncedSkillExists(self) -> bool:
		return 'hash' in self._syncState and str(self._syncState['skillId']).startswith('skill_')


	def syncSkill(self, skillDescription: str, skillIcon: str, hashComputationOnly: bool = False):
		oldInstanceExists = self.syncedSkillExists()
		oldHash = self._syncState['hash'] if oldInstanceExists else ''
		skillId = self._syncState['skillId'] if oldInstanceExists else ''
		curHash = self.skillValuesToHash(icon=skillIcon, description=skillDescription, skillId=skillId)
		changes = False

		if hashComputationOnly or (oldInstanceExists and oldHash == curHash):
			self._ctx.log.info(f'Skill model {skillId} ({self._skillName}) has no changes')
		elif oldInstanceExists:
			changes = True
			self._ctx.log.info(f'Skill model {skillId} ({self._skillName}) has been edited')
			self._ctx.skill.edit(skillId, description=skillDescription, imageKey=EnumSkillImageUrl.getResourceFileByAttr(skillIcon))
		else:
			changes = True
			skillId = self._ctx.skill.create(
				assistantId=self._assistantId,
				name=self._skillName,
				description=skillDescription,
				language=self._skillLanguage,
				imageKey=EnumSkillImageUrl.getResourceFileByAttr(skillIcon),
				attachToAssistant=True
			)
			self._ctx.log.info(f'Skill model {skillId} ({self._skillName}) has been created')
			self._createdInstances['skills'].append({'id': skillId, 'assistantId': self._assistantId})
			curHash = self.skillValuesToHash(icon=skillIcon, description=skillDescription, skillId=skillId)

		return {
			'skillId': skillId,
			'hash': curHash,
			'changes': changes
		}


	def syncSkillsOnAssistantSafely(self, typeEntityMatching: dict, skillSyncState: str = None, hashComputationOnly: bool = False):
		try:
			return self.syncSkillsOnAssistant(typeEntityMatching=typeEntityMatching, skillSyncState=skillSyncState, hashComputationOnly=hashComputationOnly)
		except:
			e = sys.exc_info()[0]
			self._ctx.log.info('Handle error gracefully')
			self._ctx.log.info(e)
			self._ctx.log.info(traceback.format_exc())
			sys.exit(-1)


	# noinspection PyUnusedLocal
	def syncSkillsOnAssistant(self, typeEntityMatching: dict = None, skillSyncState: str = None, hashComputationOnly: bool = False) -> tuple:
		#TODO this appears wrong skillSyncState is a str according to typing while self.createNewSavedSkill() returns a dict
		# is is used as a dict aswell. Is the typing wrong?
		self._syncState = skillSyncState or self.createNewSavedSkill()

		skillData = self.syncSkill(self._skill['description'], self._skill['icon'], hashComputationOnly)
		self._syncState['skillId'] = skillData['skillId']
		self._syncState['hash'] = skillData['hash']
		self._syncState['name'] = self._skillName

		return self._syncState, skillData['changes']


	def cleanCreatedInstances(self):
		self._ctx.log.info(f"[Cleanup] Deleting {len(self._createdInstances['skills'])} skills")
		for skill in self._createdInstances['skills']:
			self._ctx.skill.removeFromAssistant(assistantId=skill['assistantId'], skillId=skill['id'], deleteAfter=True)
		self._createdInstances['skills'] = list()
