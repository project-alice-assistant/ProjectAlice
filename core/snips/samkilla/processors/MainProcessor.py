import json
import typing
from pathlib import Path

from core.ProjectAliceExceptions import HttpError
from core.base.SuperManager import SuperManager
from core.snips import SamkillaManager
from core.snips.samkilla.models.EnumSkillImageUrl import EnumSkillImageUrl as EnumSkillImageUrlClass
from core.snips.samkilla.processors.IntentRemoteProcessor import IntentRemoteProcessor
from core.snips.samkilla.processors.SkillRemoteProcessor import SkillRemoteProcessor
from core.snips.samkilla.processors.SlotTypeRemoteProcessor import SlotTypeRemoteProcessor

EnumSkillImageUrl = EnumSkillImageUrlClass()


class MainProcessor:
	SAVED_ASSISTANTS_DIR = Path('var', 'assistants')
	SAVED_MODULES_DIR = 'skills'


	def __init__(self, ctx: SamkillaManager):
		self._ctx = ctx
		self._skills = dict()
		self._savedAssistants = dict()
		self._savedSlots = dict()
		self._savedIntents = dict()
		self.initSavedAssistants()
		self.initSavedSlots()
		self.initSavedIntents()


	def initSavedIntents(self):
		for lang in self.SAVED_ASSISTANTS_DIR.glob('[!.]*'):
			if not lang.is_dir(): continue

			self._savedIntents[lang.name] = dict()

			for projectId in lang.iterdir():
				directory = projectId / 'intents'
				directory.mkdir(parents=True, exist_ok=True)
				self._savedIntents[lang.name][projectId.name] = dict()

				for intent in directory.iterdir():
					intentDefinition = json.loads(intent.read_text())
					self._savedIntents[lang.name][projectId.name][intentDefinition['name']] = intentDefinition


	def initSavedSlots(self):
		for lang in self.SAVED_ASSISTANTS_DIR.glob('[!.]*'):
			if not lang.is_dir(): continue

			self._savedSlots[lang.name] = dict()

			for projectId in lang.iterdir():
				directory = projectId / 'slots'
				directory.mkdir(parents=True, exist_ok=True)
				self._savedSlots[lang.name][projectId.name] = dict()

				for slot in directory.iterdir():
					definition = json.loads(slot.read_text())
					self._savedSlots[lang.name][projectId.name][definition['name']] = definition


	def initSavedAssistants(self):
		for lang in self.SAVED_ASSISTANTS_DIR.glob('[!.]*'):
			if not lang.is_dir(): continue

			self._savedAssistants[lang.name] = dict()

			for projectId in lang.iterdir():
				filename = projectId / '_assistant.json'
				self._savedAssistants[lang.name][projectId.name] = dict()

				wholeAssistant = json.loads(filename.read_text())
				self._savedAssistants[lang.name][projectId.name] = wholeAssistant
				self.safeBaseDicts(projectId.name, lang.name)


	def hasLocalAssistantByIdAndLanguage(self, assistantLanguage: str, assistantId: str) -> bool:
		return assistantId in self._savedAssistants.get(assistantLanguage, dict())


	def getLocalFirstAssistantByLanguage(self, assistantLanguage: str, returnId: bool = False) -> typing.Any:
		assistants = self._savedAssistants.get(assistantLanguage, dict())
		if assistants:
			firstAssistant = next(iter(assistants.values()))
			return firstAssistant['id'] if returnId else firstAssistant
		return None


	def safeBaseDicts(self, assistantId: str, assistantLanguage: str):
		baseDicts = ['skills', 'slotTypes', 'intents']

		for baseDict in baseDicts:
			self._savedAssistants[assistantLanguage][assistantId].setdefault(baseDict, dict())


	def persistToLocalAssistantCache(self, assistantId: str, assistantLanguage: str):
		assistantMountpoint = self.SAVED_ASSISTANTS_DIR / assistantLanguage / assistantId
		assistantMountpoint.mkdir(parents=True, exist_ok=True)

		self.safeBaseDicts(assistantId, assistantLanguage)

		state = self._savedAssistants[assistantLanguage][assistantId]
		assistantFile = assistantMountpoint / '_assistant.json'
		assistantFile.write_text(json.dumps(state, indent=4, sort_keys=False, ensure_ascii=False))


	# self._ctx.log(f'\n[Persist] local assistant {assistantId} in {assistantLanguage}')

	def syncRemoteToLocalAssistant(self, assistantId: str, assistantLanguage: str, assistantTitle: str):
		if not self.hasLocalAssistantByIdAndLanguage(assistantId=assistantId, assistantLanguage=assistantLanguage):
			newState = {
				'id'       : assistantId,
				'name'     : assistantTitle,
				'language' : assistantLanguage,
				'skills'  : dict(),
				'slotTypes': dict(),
				'intents'  : dict()
			}

			if not assistantLanguage in self._savedAssistants:
				self._savedAssistants[assistantLanguage] = dict()

			self._savedAssistants[assistantLanguage][assistantId] = newState
			self.persistToLocalAssistantCache(assistantId=assistantId, assistantLanguage=assistantLanguage)
			self.initSavedSlots()
			self.initSavedIntents()


	def syncRemoteToLocalSkillCache(self, assistantId: str, assistantLanguage: str, skillName: str, syncState: str, persist: bool = False):
		self._savedAssistants[assistantLanguage][assistantId]['skills'][skillName] = syncState

		if persist:
			self.persistToLocalAssistantCache(assistantId=assistantId, assistantLanguage=assistantLanguage)


	def syncRemoteToLocalSlotTypeCache(self, assistantId: str, assistantLanguage: str, slotTypeName: str, syncState: str, persist: bool = False):
		self._savedAssistants[assistantLanguage][assistantId]['slotTypes'][slotTypeName] = syncState

		if persist:
			self.persistToLocalAssistantCache(assistantId=assistantId, assistantLanguage=assistantLanguage)


	def syncRemoteToLocalIntentCache(self, assistantId: str, assistantLanguage: str, intentName: str, syncState: str, persist: bool = False):
		self._savedAssistants[assistantLanguage][assistantId]['intents'][intentName] = syncState

		if persist:
			self.persistToLocalAssistantCache(assistantId=assistantId, assistantLanguage=assistantLanguage)


	def getSkillFromFile(self, skillFile: Path, skillLanguage: str) -> typing.Optional[dict]:
		try:
			skill = json.loads(Path(skillFile).read_text())

			if 'skill' not in skill:
				self._ctx.log(f"File \"{skillFile}\" has no 'skill' name definition")
				return

			skill['language'] = skillLanguage

			if skill['skill'] not in self._skills:
				self._ctx.log(f"Skill \"{skill['skill']}\" has a name different from its directory")
				return

			self._skills[skill['skill']][skillLanguage] = skill
			self._ctx.log(f"Loading skill {skill['skill']}")
			return skill

		except json.decoder.JSONDecodeError:
			self._ctx.log(f'\nInconsistent file, "{skillFile}" has a bad json format')
			return

	def getSkillSyncStateByLanguageAndAssistantId(self, skillName: str, language: str, assistantId: str) -> str:
		return self._savedAssistants.get(language, dict()).get(assistantId, dict()).get('skills', dict()).get(skillName, None)


	def getSlotTypeSyncStateByLanguageAndAssistantId(self, slotTypeName: str, language: str, assistantId: str) -> str:
		return self._savedAssistants.get(language, dict()).get(assistantId, dict()).get('slotTypes', dict()).get(slotTypeName, None)


	def getIntentSyncStateByLanguageAndAssistantId(self, intentName: str, language: str, assistantId: str) -> str:
		return self._savedAssistants.get(language, dict()).get(assistantId, dict()).get('intents', dict()).get(intentName, None)


	def persistToGlobalAssistantSlots(self, assistantId: str, assistantLanguage: str, slotNameFilter: str = None):
		assistantSlotsMountpoint = self.SAVED_ASSISTANTS_DIR / assistantLanguage / assistantId / 'slots'
		assistantSlotsMountpoint.mkdir(parents=True, exist_ok=True)

		slotTypes = self._savedSlots[assistantLanguage][assistantId]

		for key, value in slotTypes.items():
			if slotNameFilter and slotNameFilter != key: continue

			slotFile = assistantSlotsMountpoint / f'{key}.json'
			slotFile.write_text(json.dumps(value, indent=4, sort_keys=False, ensure_ascii=False))
		# self._ctx.log(f'Global slot {key}')


	def persistToGlobalAssistantIntents(self, assistantId: str, assistantLanguage: str, intentNameFilter: str = None):
		assistantSlotsMountpoint = self.SAVED_ASSISTANTS_DIR / assistantLanguage / assistantId / 'intents'
		assistantSlotsMountpoint.mkdir(parents=True, exist_ok=True)

		intents = self._savedIntents[assistantLanguage][assistantId]

		for key, value in intents.items():
			if intentNameFilter and intentNameFilter != key: continue

			intentFile = assistantSlotsMountpoint / f'{key}.json'
			intentFile.write_text(json.dumps(value, indent=4, sort_keys=False, ensure_ascii=False))
		# self._ctx.log(f'Global slot {key}')


	def syncGlobalSlotType(self, assistantId: str, assistantLanguage: str, slotTypeName: str, slotDefinition: str, persist: bool = False):
		self._savedSlots[assistantLanguage][assistantId][slotTypeName] = slotDefinition

		if persist:
			self.persistToGlobalAssistantSlots(assistantId=assistantId, assistantLanguage=assistantLanguage, slotNameFilter=slotTypeName)


	def syncGlobalIntent(self, assistantId: str, assistantLanguage: str, intentName: str, intentDefinition: str, persist: bool = False):
		self._savedIntents[assistantLanguage][assistantId][intentName] = intentDefinition

		if persist:
			self.persistToGlobalAssistantIntents(assistantId=assistantId, assistantLanguage=assistantLanguage, intentNameFilter=intentName)


	def mergeSkillSlotTypes(self, slotTypesSkillsValues: dict, assistantId: str, slotLanguage: str = None):
		mergedSlotTypes = dict()
		slotTypesGlobalValues = dict()

		for slotName in slotTypesSkillsValues:
			if slotName in self._savedSlots[slotLanguage][assistantId]:
				savedSlotType = self._savedSlots[slotLanguage][assistantId][slotName]

				slotTypesGlobalValues[savedSlotType['name']] = {'__otherattributes__': {
					'name'                   : savedSlotType['name'],
					'matchingStrictness'     : savedSlotType['matchingStrictness'],
					'automaticallyExtensible': savedSlotType['automaticallyExtensible'],
					'useSynonyms'            : savedSlotType['useSynonyms'],
					'values'                 : list()
				}}

				for savedSlotValue in savedSlotType['values']:
					if savedSlotValue['value'] not in slotTypesGlobalValues[savedSlotType['name']]:
						slotTypesGlobalValues[savedSlotType['name']][savedSlotValue['value']] = dict()

						if 'synonyms' in savedSlotValue:
							for synonym in savedSlotValue['synonyms']:
								if not synonym: continue
								slotTypesGlobalValues[savedSlotType['name']][savedSlotValue['value']].setdefault(synonym, True)

		for slotName, slotValue in slotTypesSkillsValues.items():
			slotTypeCatalogValues = slotTypesGlobalValues.get(slotName, slotValue)

			mergedSlotTypes[slotName] = slotTypeCatalogValues.pop('__otherattributes__')
			mergedSlotTypes[slotName]['values'] = [{'value': key, 'synonyms': list(value)} for key, value in slotTypeCatalogValues.items()]

			self.syncGlobalSlotType(
				assistantId=assistantId,
				assistantLanguage=slotLanguage,
				slotTypeName=slotName,
				slotDefinition=mergedSlotTypes[slotName],
				persist=True
			)

		return mergedSlotTypes


	def mergeSkillIntents(self, intentsSkillsValues: dict, assistantId: str, intentLanguage: str = None) -> dict:
		mergedIntents = dict()
		intentsGlobalValues = dict()

		for intentName in intentsSkillsValues:
			if intentName in self._savedIntents[intentLanguage][assistantId]:
				savedIntent = self._savedIntents[intentLanguage][assistantId][intentName]

				intentsGlobalValues[savedIntent['name']] = {
					'__otherattributes__': {
						'name'            : savedIntent['name'],
						'description'     : savedIntent['description'],
						'enabledByDefault': savedIntent['enabledByDefault'],
						'utterances'      : list(),
						'slots'           : list()
					},
					'utterances'         : dict(),
					'slots'              : dict()
				}

				for savedUtterance in savedIntent['utterances']:
					intentsGlobalValues[savedIntent['name']]['utterances'].setdefault(savedUtterance, True)

				for skillSlot in savedIntent['slots']:
					intentsGlobalValues[savedIntent['name']]['slots'].setdefault(skillSlot['name'], skillSlot)

		for intentName, intentValue in intentsSkillsValues.items():
			intentCatalogValues = intentsGlobalValues.get(intentName, intentValue)

			mergedIntents[intentName] = intentCatalogValues['__otherattributes__']
			mergedIntents[intentName]['utterances'] = list(intentCatalogValues['utterances'])
			mergedIntents[intentName]['slots'] = list(intentCatalogValues['slots'].values())

			self.syncGlobalIntent(
				assistantId=assistantId,
				assistantLanguage=intentLanguage,
				intentName=intentName,
				intentDefinition=mergedIntents[intentName],
				persist=True
			)

		return mergedIntents


	# noinspection PyUnusedLocal
	def buildMapsFromDialogTemplates(self, runOnAssistantId: str = None, skillFilter: list = None, languageFilter: str = None) -> tuple:
		if skillFilter is None:
			skillFilter = list()

		self._skills = dict()

		rootDir = Path('skills')
		rootDir.mkdir(exist_ok=True)

		slotTypesSkillsValues = dict()
		intentsSkillsValues = dict()
		intentNameSkillMatching = dict()

		for skillPath in rootDir.iterdir():
			intentsPath = skillPath / 'dialogTemplate'

			if not intentsPath.is_dir(): continue

			self._skills[skillPath.name] = dict()

			for languageFile in intentsPath.iterdir():
				language = languageFile.stem
				if languageFilter and languageFilter != language: continue

				skill = self.getSkillFromFile(skillFile=languageFile, skillLanguage=language)
				if not skill:
					return None, None, None

				# We need all slotTypes values of all skills, even if there is a skill filter
				for skillSlotType in skill['slotTypes']:
					if skillSlotType['name'] not in slotTypesSkillsValues:
						slotTypesSkillsValues[skillSlotType['name']] = {
							'__otherattributes__': {
								'name'                   : skillSlotType['name'],
								'matchingStrictness'     : skillSlotType['matchingStrictness'],
								'automaticallyExtensible': skillSlotType['automaticallyExtensible'],
								'useSynonyms'            : skillSlotType['useSynonyms'],
								'values'                 : list()
							}
						}

					for skillSlotValue in skillSlotType['values']:
						if skillSlotValue['value'] not in slotTypesSkillsValues[skillSlotType['name']]:
							slotTypesSkillsValues[skillSlotType['name']][skillSlotValue['value']] = dict()

							for synonym in skillSlotValue.get('synonyms', list()):
								if not synonym: continue
								slotTypesSkillsValues[skillSlotType['name']][skillSlotValue['value']][synonym] = True

				# We need all intents values of all skills, even if there is a skill filters
				for skillIntent in skill['intents']:
					if skillIntent['name'] not in intentsSkillsValues:
						intentNameSkillMatching[skillIntent['name']] = skillPath.name

						intentsSkillsValues[skillIntent['name']] = {
							'__otherattributes__': {
								'name'            : skillIntent['name'],
								'description'     : skillIntent['description'],
								'enabledByDefault': skillIntent['enabledByDefault'],
								'utterances'      : list(),
								'slots'           : list()
							},
							'utterances'         : dict(),
							'slots'              : dict()
						}

					for skillUtterance in skillIntent.get('utterances', list()):
						intentsSkillsValues[skillIntent['name']]['utterances'].setdefault(skillUtterance, True)

					for skillSlot in skillIntent.get('slots', list()):
						intentsSkillsValues[skillIntent['name']]['slots'].setdefault(skillSlot['name'], skillSlot)

				if skillFilter and skillPath.name not in skillFilter:
					del self._skills[skill['skill']]

		return slotTypesSkillsValues, intentsSkillsValues, intentNameSkillMatching


	# TODO to refacto in different method of a new Processor
	def syncLocalToRemote(self, runOnAssistantId: str, skillFilter: list = None, languageFilter: str = None) -> bool:

		slotTypesSkillsValues, intentsSkillsValues, intentNameSkillMatching = self.buildMapsFromDialogTemplates(
			runOnAssistantId=runOnAssistantId,
			skillFilter=skillFilter,
			languageFilter=languageFilter
		)

		if not slotTypesSkillsValues or not intentsSkillsValues or not intentNameSkillMatching:
			return False

		# Get a dict with all slotTypes
		typeEntityMatching, globalChangesSlotTypes = self.syncLocalToRemoteSlotTypes(
			slotTypesSkillsValues,
			runOnAssistantId,
			languageFilter,
			skillFilter
		)

		skillNameIdMatching, globalChangesSkills = self.syncLocalToRemoteSkills(
			typeEntityMatching,
			runOnAssistantId,
			languageFilter,
			skillFilter
		)

		globalChangesIntents = self.syncLocalToRemoteIntents(
			skillNameIdMatching,
			intentNameSkillMatching,
			typeEntityMatching,
			intentsSkillsValues,
			runOnAssistantId,
			languageFilter,
			skillFilter
		)

		return globalChangesSlotTypes or globalChangesSkills or globalChangesIntents


	# noinspection PyUnusedLocal
	def syncLocalToRemoteSlotTypes(self, slotTypesSkillsValues: dict, runOnAssistantId: str, languageFilter: str = None, skillFilter: list = None) -> tuple:
		slotTypesSynced = dict()
		globalChanges = False

		mergedSlotTypes = self.mergeSkillSlotTypes(
			slotTypesSkillsValues=slotTypesSkillsValues,
			assistantId=runOnAssistantId,
			slotLanguage=languageFilter
		)

		typeEntityMatching = dict()

		for slotName, slotType in mergedSlotTypes.items():

			slotSyncState = self.getSlotTypeSyncStateByLanguageAndAssistantId(
				slotTypeName=slotName,
				language=languageFilter,
				assistantId=runOnAssistantId
			)

			slotRemoteProcessor = SlotTypeRemoteProcessor(
				ctx=self._ctx,
				slotType=slotType,
				slotLanguage=languageFilter,
				assistantId=runOnAssistantId,
			)

			newSlotTypeSyncState, changes = slotRemoteProcessor.syncSlotTypesOnAssistantSafely(
				slotTypeSyncState=slotSyncState,
				hashComputationOnly=False
			)

			if changes: globalChanges = True

			typeEntityMatching[slotName] = newSlotTypeSyncState

			self.syncRemoteToLocalSlotTypeCache(
				assistantId=runOnAssistantId,
				assistantLanguage=languageFilter,
				slotTypeName=slotName,
				syncState=newSlotTypeSyncState,
				persist=True
			)

			slotTypesSynced[slotName] = True

		# Remove deprecated/renamed slotTypes
		hasDeprecatedSlotTypes = list()

		for slotTypeName in self._savedAssistants[languageFilter][runOnAssistantId]['slotTypes']:
			if slotTypeName not in slotTypesSynced:
				self._ctx.log(f'Deprecated slotType {slotTypeName}')
				slotTypeCacheData = self._savedAssistants[languageFilter][runOnAssistantId]['slotTypes'][slotTypeName]

				entityId = slotTypeCacheData['entityId']
				self._ctx.entity.delete(entityId=entityId, language=languageFilter)

				hasDeprecatedSlotTypes.append(slotTypeName)

		if hasDeprecatedSlotTypes:
			globalChanges = True

			for slotTypeName in hasDeprecatedSlotTypes:
				del self._savedAssistants[languageFilter][runOnAssistantId]['slotTypes'][slotTypeName]

				if slotTypeName in self._savedSlots[languageFilter][runOnAssistantId]:
					del self._savedSlots[languageFilter][runOnAssistantId][slotTypeName]

					globalSlotTypeFile = self.SAVED_ASSISTANTS_DIR / languageFilter / runOnAssistantId / 'slots' / f'{slotTypeName}.json'

					if globalSlotTypeFile.exists():
						globalSlotTypeFile.unlink()

			self.persistToLocalAssistantCache(assistantId=runOnAssistantId, assistantLanguage=languageFilter)

		return typeEntityMatching, globalChanges


	# noinspection PyUnusedLocal
	def syncLocalToRemoteIntents(self, skillNameIdMatching: dict, intentNameSkillMatching: dict, typeEntityMatching: dict, intentsSkillsValues: dict,
	                             runOnAssistantId: str, languageFilter: str = None, skillFilter: list = None) -> bool:

		intentsSynced = dict()
		globalChanges = False

		mergedIntents = self.mergeSkillIntents(
			intentsSkillsValues=intentsSkillsValues,
			assistantId=runOnAssistantId,
			intentLanguage=languageFilter
		)

		for intentName, intent in mergedIntents.items():

			intentSyncState = self.getIntentSyncStateByLanguageAndAssistantId(
				intentName=intentName,
				language=languageFilter,
				assistantId=runOnAssistantId
			)

			intentRemoteProcessor = IntentRemoteProcessor(
				ctx=self._ctx,
				intent=intent,
				intentLanguage=languageFilter,
				assistantId=runOnAssistantId,
			)

			if intentName not in intentNameSkillMatching or intentNameSkillMatching[intentName] not in skillNameIdMatching:
				intentsSynced[intentName] = True
				continue

			skillId = skillNameIdMatching[intentNameSkillMatching[intentName]]

			newIntentSyncState, changes = intentRemoteProcessor.syncIntentsOnAssistantSafely(
				typeEntityMatching=typeEntityMatching,
				skillId=skillId,
				intentSyncState=intentSyncState,
				hashComputationOnly=False
			)

			if changes: globalChanges = True

			self.syncRemoteToLocalIntentCache(
				assistantId=runOnAssistantId,
				assistantLanguage=languageFilter,
				intentName=intentName,
				syncState=newIntentSyncState,
				persist=True
			)

			intentsSynced[intentName] = True

		# Remove deprecated/renamed slotTypes
		hasDeprecatedIntents = list()

		for intentName in self._savedAssistants[languageFilter][runOnAssistantId]['intents']:
			if intentName not in intentsSynced:
				self._ctx.log(f'Deprecated intent {intentName}')
				intentCacheData = self._savedAssistants[languageFilter][runOnAssistantId]['intents'][intentName]

				intentId = intentCacheData['intentId']

				try:
					self._ctx.intent.delete(intentId=intentId)

				except HttpError as he:
					isAttachToSkillIds = (json.loads(json.loads(he.message)['message'])['skillIds'])

					for isAttachToSkillId in isAttachToSkillIds:
						self._ctx.intent.removeFromSkill(intentId=intentId, skillId=isAttachToSkillId, userId=self._ctx.userId, deleteAfter=False)

					self._ctx.intent.delete(intentId=intentId)

				hasDeprecatedIntents.append(intentName)

		if hasDeprecatedIntents:
			globalChanges = True

			for intentName in hasDeprecatedIntents:
				del self._savedAssistants[languageFilter][runOnAssistantId]['intents'][intentName]

				if intentName in self._savedIntents[languageFilter][runOnAssistantId]:
					del self._savedIntents[languageFilter][runOnAssistantId][intentName]

					globalIntentFile = self.SAVED_ASSISTANTS_DIR / languageFilter / runOnAssistantId / 'intents' / f'{intentName}.json'

					if globalIntentFile.exists():
						globalIntentFile.unlink()

			self.persistToLocalAssistantCache(assistantId=runOnAssistantId, assistantLanguage=languageFilter)

		return globalChanges


	def syncLocalToRemoteSkills(self, typeEntityMatching: dict, runOnAssistantId: str, languageFilter: str = None, skillFilter: list = None):
		skillsSynced = dict()
		globalChanges = False

		skillNameIdMatching = dict()

		for skillName, skillSettings in self._skills.items():
			if languageFilter not in skillSettings:
				continue

			skillSyncState = self.getSkillSyncStateByLanguageAndAssistantId(
				skillName=skillName,
				language=languageFilter,
				assistantId=runOnAssistantId
			)

			# Start a SkillRemoteProcessor tasker for each skill(a.k.a skill)
			skillRemoteProcessor = SkillRemoteProcessor(
				ctx=self._ctx,
				assistantId=runOnAssistantId,
				skill=skillSettings[languageFilter],
				skillName=skillName,
				skillLanguage=languageFilter
			)

			newSkillSyncState, changes = skillRemoteProcessor.syncSkillsOnAssistantSafely(
				typeEntityMatching=typeEntityMatching,
				skillSyncState=skillSyncState,
				hashComputationOnly=False
			)

			if changes: globalChanges = True

			skillNameIdMatching[skillName] = newSkillSyncState['skillId']

			self.syncRemoteToLocalSkillCache(
				assistantId=runOnAssistantId,
				assistantLanguage=languageFilter,
				skillName=skillName,
				syncState=newSkillSyncState,
				persist=True
			)

			skillsSynced[skillName] = True

		# Remove deprecated/renamed skills
		hasDeprecatedSkills = list()

		for skillName in self._savedAssistants[languageFilter][runOnAssistantId]['skills']:
			if skillFilter and skillName not in skillFilter:
				continue

			if skillName not in skillsSynced:
				self._ctx.log(f'Deprecated skill {skillName}')
				skillCacheData = self._savedAssistants[languageFilter][runOnAssistantId]['skills'][skillName]
				skillId = skillCacheData['skillId']

				for slotTypeName in skillCacheData.get('slotTypes', list()):
					entityId = skillCacheData['slotTypes'][slotTypeName]['entityId']
					self._ctx.entity.delete(entityId=entityId, language=languageFilter)

				for intentName in skillCacheData.get('intents', list()):
					intentId = skillCacheData['intents'][intentName]['intentId']
					self._ctx.intent.removeFromSkill(userId=self._ctx.userId, skillId=skillId, intentId=intentId, deleteAfter=True)

				self._ctx.skill.removeFromAssistant(assistantId=runOnAssistantId, skillId=skillId, deleteAfter=True)

				hasDeprecatedSkills.append(skillName)

		if hasDeprecatedSkills:
			globalChanges = True

			for skillName in hasDeprecatedSkills:
				del self._savedAssistants[languageFilter][runOnAssistantId]['skills'][skillName]

			self.persistToLocalAssistantCache(assistantId=runOnAssistantId, assistantLanguage=languageFilter)

		return skillNameIdMatching, globalChanges


	# TODO to refacto in different method of a new Processor
	def syncRemoteToLocal(self, runOnAssistantId: str, skillFilter: list = None, languageFilter: str = None):

		# Build cache
		self._ctx.entity.listEntitiesByUserEmail(userEmail=self._ctx.userEmail, returnAllCacheIndexedBy='id')
		remoteIndexedIntents = self._ctx.intent.listIntentsByUserId(userId=self._ctx.userId, returnAllCacheIndexedBy='id')
		remoteIndexedSkills = self._ctx.skill.listSkillsByUserId(userId=self._ctx.userId, returnAllCacheIndexedBy='id')
		hasFork = False

		# Check for fork and execute fork if needed
		for assistant in self._ctx.assistant.list(rawResponse=True)['assistants']:
			if assistant['id'] != runOnAssistantId:
				continue

			for skill in assistant['skills']:
				skillId = skill['id']

				if skillId not in remoteIndexedSkills:
					skillId = self._ctx.assistant.forkAssistantSkill(assistantId=runOnAssistantId, sourceSkillId=skillId)
					self._ctx.log(f"[Forked] Skill from {skill['id']} to {skillId}")
					hasFork = True

				for intent in skill['intents']:
					intentId = intent['id']

					if intentId not in remoteIndexedIntents:
						intentId = self._ctx.skill.forkSkillIntent(skillId=skillId, sourceIntentId=intentId, userId=self._ctx.userId)
						self._ctx.log(f"[Forked] Intent from {skill['id']} to {intentId} used in skill {skillId}")
						hasFork = True

		if hasFork:
			# Rebuild cache
			self._ctx.entity.listEntitiesByUserEmail(userEmail=self._ctx.userEmail)
			self._ctx.intent.listIntentsByUserId(userId=self._ctx.userId)
			self._ctx.skill.listSkillsByUserId(userId=self._ctx.userId)

		# Build each skill configuration
		skills = dict()

		cachedIndexedSkills = self._ctx.skill.listSkillsByUserIdAndAssistantId(userId=self._ctx.userId, assistantId=runOnAssistantId, fromCache=True)

		for skill in cachedIndexedSkills:
			skillName = SuperManager.getInstance().commons.toCamelCase(string=skill['name'], replaceSepCharacters=True, sepCharacters=('/', '-', '_'))

			if skillFilter and skillName not in skillFilter:
				continue

			skills[skillName] = {
				'skill'     : skillName,
				'icon'       : EnumSkillImageUrl.urlToResourceKey(skill['imageUrl']),
				'description': skill['description'],
				'slotTypes'  : list(),
				'intents'    : list()
			}
			skillSyncState = {
				'skillId'  : skill['id'],
				'name'     : skillName,
				'slotTypes': dict(),
				'intents'  : dict(),
				'hash'     : ''
			}

			cachedIndexedIntents = self._ctx.intent.listIntentsByUserIdAndSkillId(userId=self._ctx.userId, skillId=skill['id'], fromCache=True)
			typeEntityMatching = dict()

			for intent in cachedIndexedIntents:
				intentName = intent['name']

				if intentName.startswith(skill['name'] + '_'):
					intentName = intentName.replace(skill['name'] + '_', '')

				intentName = SuperManager.getInstance().commons.toCamelCase(string=intentName, replaceSepCharacters=True, sepCharacters=('/', '-', '_'))

				utterances = list()
				objectUtterances = self._ctx.intent.listUtterancesByIntentId(intentId=intent['id'])

				slotIdAndNameMatching = {slot['id']: slot for slot in intent['slots']}

				for objectUtterance in objectUtterances:
					text = objectUtterance['text']
					positionOffset = 0

					for hole in objectUtterance['data']:
						word = hole['text']
						start = hole['range']['start'] + positionOffset
						end = hole['range']['end'] + positionOffset
						slotName = slotIdAndNameMatching[hole['slotId']]['name']
						slotName = SuperManager.getInstance().commons.toCamelCase(string=slotName, replaceSepCharacters=True, sepCharacters=('/', '-', '_'))
						newWord = '{' + word + self._ctx.intent.GLUE_SLOT_WORD + slotName + '}'
						text = text[:start] + newWord + text[end:]
						positionOffset += len(newWord) - len(word)

					utterances.append(text)

				cachedIndexedEntities = self._ctx.entity.listEntitiesByUserEmailAndIntentId(userEmail=self._ctx.userEmail, intentId=intent['id'], fromCache=True)

				for entity in cachedIndexedEntities:
					if entity['id'] in typeEntityMatching:
						continue

					values = self._ctx.entity.listEntityValuesByEntityId(entityId=entity['id'])
					entityName = SuperManager.getInstance().commons.toCamelCase(string=entity['name'], replaceSepCharacters=True, sepCharacters=('/', '-', '_'))
					typeEntityMatching[entity['id']] = entityName

					skills[skillName]['slotTypes'].append({
						'name'                   : entityName,
						'matchingStrictness'     : entity['matchingStrictness'],
						'automaticallyExtensible': entity['automaticallyExtensible'],
						'useSynonyms'            : entity['useSynonyms'],
						'values'                 : values
					})
					skillSyncState['slotTypes'][entityName] = {
						'entityId': entity['id'],
						'hash'    : ''
					}

				slots = [{
					'name'           : SuperManager.getInstance().commons.toCamelCase(string=slot['name'], replaceSepCharacters=True, sepCharacters=('/', '-', '_')),
					'description'    : slot['description'],
					'required'       : slot['required'],
					'type'           : slot['entityId'] if slot['entityId'].startswith('snips/') else typeEntityMatching[slot['entityId']],
					'missingQuestion': slot['missingQuestion']
				} for slot in intent['slots']]

				skills[skillName]['intents'].append({
					'name'            : intentName,
					'description'     : intent['description'],
					'enabledByDefault': intent['enabledByDefault'],
					'utterances'      : utterances,
					'slots'           : slots
				})
				skillSyncState['intents'][intentName] = {
					'intentId': intent['id'],
					'hash'    : ''
				}

			# Persist skill configuration
			skillConfig = skills[skillName]
			skillIntentsMountpoint = Path(self.SAVED_MODULES_DIR, skillName, 'dialogTemplate')
			skillIntentsMountpoint.mkdir(parents=True, exist_ok=True)

			skillIntentsOutputFile = skillIntentsMountpoint / f'{languageFilter}.json'

			skillIntentsOutputFile.write_text(json.dumps(skillConfig, indent=4, sort_keys=False, ensure_ascii=False))
			self._ctx.log(f'Finished for skill {skillName}')
