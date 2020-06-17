import json
from pathlib import Path

import re

from core.ProjectAliceExceptions import LanguageManagerLangNotSupported
from core.base.model.Manager import Manager


class LanguageManager(Manager):

	def __init__(self):
		super().__init__()
		self._supportedLanguages = list()
		self._activeLanguage = ''
		self._activeCountryCode = ''
		self._defaultLanguage = ''
		self._defaultCountryCode = ''
		self._overrideLanguage = ''
		self._overrideCountryCode = ''

		self._stringsData = dict()
		self._locals = list()

		self._floatExpressionPattern = re.compile(r'([0-9]+\.[0-9]+)')
		self._mathSigns = ('+', '-', '/', '*', '%')

		self._loadSupportedLanguages()


	def onStart(self):
		super().onStart()
		self.loadSystemStrings()


	def onBooted(self):
		data = self.TalkManager.langData
		if self._name in data:
			self._locals = data[self._name]


	def sanitizeNluQuery(self, query: str = '') -> str:
		for sign, langsValues in self._stringsData['system'].items():
			if sign in self._mathSigns:
				if sign == '-':
					query = query.replace(f' {sign} ', langsValues[self.activeLanguage][0])
				else:
					query = query.replace(sign, langsValues[self.activeLanguage][0])

		return query


	def loadSystemStrings(self):
		with open(Path('system/manager/LanguageManager/strings.json')) as jsonFile:
			self._stringsData['system'] = json.load(jsonFile)


	def loadSkillStrings(self, skillName: str):
		skillInstance = self.SkillManager.getSkillInstance(skillName)
		if not skillInstance:
			self.logError(f'Loading strings for skill **{skillName}** failed')

		jsonFile = skillInstance.getResource('strings.json')
		if not jsonFile.exists():
			# Not all skills come with one
			return

		try:
			self._stringsData[skillName] = json.loads(jsonFile.read_text())
		except ValueError:
			self.logError(f'String file for skill **{skillName}** is corrupted')


	def getTranslations(self, skill: str, key: str, toLang: str = '') -> list:
		if not toLang:
			toLang = self.activeLanguage

		if skill not in self._stringsData:
			self.logError(f'Asked to get translation for **{key}** from skill **{skill}** but skill does not exist')
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
		activeCountryCode = self.ConfigManager.getAliceConfigByName('activeCountryCode')
		langDef: dict = self.ConfigManager.getAliceConfigByName('supportedLanguages')

		if self.ConfigManager.getAliceConfigByName('nonNativeSupportLanguage'):
			if self.ConfigManager.getAliceConfigByName('stayCompletlyOffline'):
				self.logWarning(f'You cannot use a non natively support language if you have chosen to stay completly offline.')
			else:
				self.logWarning(f'You are using a non natively supported language **{self.ConfigManager.getAliceConfigByName("nonNativeSupportLanguage")}**')
				self._activeLanguage = 'en'
				self._activeCountryCode = 'US'
				self._defaultLanguage = 'en'
				self._defaultCountryCode = 'US'
				self._overrideLanguage = self.ConfigManager.getAliceConfigByName('nonNativeSupportLanguage')
				self._overrideCountryCode = self.ConfigManager.getAliceConfigByName('nonNativeSupportCountry')
				return

		for langCode, settings in langDef.items():
			self._supportedLanguages.append(langCode)
			if settings['default']:
				self._defaultLanguage = langCode
				self._defaultCountryCode = settings['defaultCountryCode']

			if langCode == activeLangDef:
				self._activeLanguage = langCode

				if activeCountryCode in settings['countryCodes']:
					self._activeCountryCode = activeCountryCode
				else:
					self.logWarning(f'Country code **{activeCountryCode}** is not supported, falling back to **{self._defaultCountryCode}**')
					self._activeCountryCode = self._defaultCountryCode

		if not self._activeLanguage and self._defaultLanguage:
			self.logWarning(f'No active language defined, falling back to **{self._defaultLanguage}**')
			self._activeLanguage = self._defaultLanguage
			self._activeCountryCode = self._defaultCountryCode

		elif self._activeLanguage and not self._defaultLanguage:
			self.logWarning(f'No default language defined, falling back to **{self._activeLanguage}**')
			self._defaultLanguage = self._activeLanguage
			self._defaultCountryCode = self._activeCountryCode

		elif self._activeLanguage and self._defaultLanguage:
			self.logInfo(f'Active language set to **{self.activeLanguageAndCountryCode}**')
			self.logInfo(f'Default language set to **{self.defaultLanguage}-{self.defaultCountryCode}**')

		else:
			self.logWarning('No active language or default language defined, falling back to **en-US**')
			self._activeLanguage = self._defaultLanguage = 'en'
			self._activeCountryCode = self._defaultCountryCode = 'US'


	def localize(self, string: str) -> str:
		string = string.lower()

		if self._activeLanguage == 'fr':
			for match in re.findall(self._floatExpressionPattern, string):
				matching = match.replace('.', ',')
				string = string.replace(match, matching)

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


	@property
	def activeLanguage(self) -> str:
		return self._activeLanguage


	@property
	def overrideLanguage(self) -> str:
		return self._overrideLanguage


	@property
	def defaultLanguage(self) -> str:
		return self._defaultLanguage


	@property
	def activeCountryCode(self) -> str:
		return self._activeCountryCode


	@property
	def overrideCountryCode(self) -> str:
		return self._overrideCountryCode


	@property
	def defaultCountryCode(self) -> str:
		return self._defaultCountryCode


	@property
	def activeLanguageAndCountryCode(self) -> str:
		return f'{self._activeLanguage}-{self._activeCountryCode}'


	@property
	def overrideLanguageAndCountryCode(self) -> str:
		return f'{self._overrideLanguage}-{self._overrideCountryCode}'


	def getLanguageAndCountryCode(self, allowOverride: bool = True) -> str:
		return self.overrideLanguageAndCountryCode if allowOverride and self.overrideLanguage else self.activeLanguageAndCountryCode


	@property
	def supportedLanguages(self) -> list:
		return self._supportedLanguages
