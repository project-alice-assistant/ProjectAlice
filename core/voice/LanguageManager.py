import json
import re
from pathlib import Path
from typing import Optional

from core.ProjectAliceExceptions import LanguageManagerLangNotSupported
from core.base.model.Manager import Manager


class LanguageManager(Manager):

	NAME = 'LanguageManager'

	def __init__(self):
		super().__init__(self.NAME)
		self._supportedLanguages 		= list()
		self._activeLanguage 			= ''
		self._activeCountryCode 		= ''
		self._defaultLanguage 			= ''
		self._defaultCountryCode 		= ''
		self._activeSnipsProjectId 		= ''

		self._stringsData 				= dict()
		self._locals 					= list()

		self._floatExpressionPattern 	= re.compile(r'([0-9]+\.[0-9]+)')
		self._mathSigns                 = ('+', '-', '/', '*', '%')


	def onStart(self):
		super().onStart()
		self._loadSupportedLanguages()
		self.loadStrings()


	def onBooted(self):
		data = self.TalkManager.langData
		if self.NAME in data:
			self._locals = data[self.NAME]


	def sanitizeNluQuery(self, query: str = '') -> str:
		for sign, langsValues in self._stringsData['system'].items():
			if sign in self._mathSigns:
				if sign == '-':
					query = query.replace(' ' + sign + ' ', langsValues[self.activeLanguage][0])
				else:
					query = query.replace(sign, langsValues[self.activeLanguage][0])

		return query


	def loadStrings(self, skillToLoad: str = ''):
		with open(Path('system/manager/LanguageManager/strings.json')) as jsonFile:
			self._stringsData['system'] = json.load(jsonFile)

		for skillName in self.ConfigManager.skillsConfigurations:
			if skillToLoad and skillName != skillToLoad:
				continue

			try:
				jsonFile = Path('skills', skillName, 'strings.json')
				self._stringsData[skillName] = json.loads(jsonFile.read_text())
			except FileNotFoundError:
				continue
			except ValueError:
				continue


	def getTranslations(self, skill: str, key: str, toLang: str = '') -> Optional[list]:
		if not toLang:
			toLang = self.activeLanguage
		if not skill in self._stringsData:
			self.logError(f'Asked to get translation from skill "{skill}" but does not exist')
			return list()
		elif key not in self._stringsData[skill]:
			self.logError(f'Asked to get translation for "{key}" from skill "{skill}" but does not exist')
			return list()
		elif toLang not in self._stringsData[skill][key]:
			self.logError(f'Asked to get "{toLang}" translation for "{key}" from skill "{skill}" but does not exist')
			return list()
		else:
			return self._stringsData[skill][key][toLang]


	def getStrings(self, key: str, skill: str = 'system') -> list:
		return self.getTranslations(skill, key, self._activeLanguage)


	def _loadSupportedLanguages(self):
		activeLangDef: str = self.ConfigManager.getAliceConfigByName('activeLanguage')
		langDef: dict = self.ConfigManager.getAliceConfigByName('supportedLanguages')

		for langCode, settings in langDef.items():
			self._supportedLanguages.append(langCode)
			if settings['default']:
				self._defaultLanguage = langCode
				self._defaultCountryCode = settings['countryCode']

			if langCode == activeLangDef:
				self._activeLanguage = langCode
				self._activeCountryCode = settings['countryCode']
				self._activeSnipsProjectId = settings['snipsProjectId']

		if not self._activeLanguage and self._defaultLanguage:
			self.logWarning(f'No active language defined, falling back to {self._defaultLanguage}')
			self._activeLanguage = self._defaultLanguage
			self._activeCountryCode = self._defaultCountryCode

		elif self._activeLanguage and not self._defaultLanguage:
			self.logWarning(f'No default language defined, falling back to {self._activeLanguage}')
			self._defaultLanguage = self._activeLanguage
			self._defaultCountryCode = self._activeCountryCode

		elif self._activeLanguage and self._defaultLanguage:
			self.logInfo(f'Active language set to "{self.activeLanguageAndCountryCode}"')
			self.logInfo(f'Default language set to "{self.defaultLanguage}-{self.defaultCountryCode}"')

		else:
			self.logWarning('No active language or default language defined, falling back to "en"')
			self._activeLanguage = self._defaultLanguage = 'en'
			self._activeCountryCode = self._defaultCountryCode = 'US'


		if not self._activeSnipsProjectId:
			self.logInfo('No active snips project id set')


	def localize(self, string: str) -> str:
		string = string.lower()

		if self._activeLanguage == 'fr':
			for match in re.findall(self._floatExpressionPattern, string):
				m = match.replace('.', ',')
				string = string.replace(match, m)

		for key in self._locals:
			if key in string:
				string = string.replace(key, self._locals[key][self._activeLanguage])
				break

		return string


	def changeActiveLanguage(self, toLang: str):
		toLang = toLang.lower()

		if toLang not in self._supportedLanguages:
			raise LanguageManagerLangNotSupported

		self.ConfigManager.changeActiveLanguage(toLang)
		self._loadSupportedLanguages()


	def changeActiveSnipsProjectIdForLanguage(self, projectId: str, forLang: str):
		forLang = forLang.lower()

		if forLang not in self._supportedLanguages:
			raise LanguageManagerLangNotSupported

		self.ConfigManager.changeActiveSnipsProjectIdForLanguage(projectId, forLang)
		self._loadSupportedLanguages()


	@property
	def activeSnipsProjectId(self) -> str:
		return self._activeSnipsProjectId


	@property
	def activeLanguage(self) -> str:
		return self._activeLanguage


	@property
	def defaultLanguage(self) -> str:
		return self._defaultLanguage


	@property
	def activeCountryCode(self) -> str:
		return self._activeCountryCode


	@property
	def defaultCountryCode(self) -> str:
		return self._defaultCountryCode


	@property
	def activeLanguageAndCountryCode(self) -> str:
		return f'{self._activeLanguage}-{self._activeCountryCode}'
