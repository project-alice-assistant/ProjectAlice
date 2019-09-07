import json
from pathlib import Path
from typing import Optional

import re

from core.ProjectAliceExceptions import LanguageManagerLangNotSupported
from core.base.Manager import Manager
from core.base.SuperManager import SuperManager


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
	def activeLanguageAndCountryCode(self):
		return '{}-{}'.format(self._activeLanguage, self._activeCountryCode)


	def onStart(self):
		super().onStart()
		self._loadSupportedLanguages()
		self.loadStrings()


	def onBooted(self):
		data = SuperManager.getInstance().talkManager.langData
		if self.NAME in data:
			self._locals = data[self.NAME]


	def sanitizeNluQuery(self, query: str = '') -> str:
		for sign, langsValues in self._stringsData['system'].items():
			if len(sign) == 1:
				if sign == '-':
					query = query.replace(' ' + sign + ' ', langsValues[self.activeLanguage][0])
				else:
					query = query.replace(sign, langsValues[self.activeLanguage][0])

		return query


	def loadStrings(self, moduleToLoad: str = ''):
		with open(Path('system/manager/LanguageManager/strings.json')) as jsonFile:
			self._stringsData['system'] = json.load(jsonFile)

		for moduleName in SuperManager.getInstance().configManager.modulesConfigurations:
			if moduleToLoad and moduleName != moduleToLoad:
				continue

			try:
				jsonFile = Path('modules', moduleName, 'strings.json')
				self._stringsData[moduleName] = json.loads(jsonFile.read_text())
			except FileNotFoundError:
				continue
			except ValueError:
				continue


	def getTranslations(self, module: str, key: str, toLang: str = '') -> Optional[list]:
		if not toLang:
			toLang = self.activeLanguage
		if not module in self._stringsData:
			self._logger.error('[{}] Asked to get translation from module "{}" but does not exist'.format(self.name, module))
			return list()
		elif key not in self._stringsData[module]:
			self._logger.error('[{}] Asked to get translation for "{}" from module "{}" but does not exist'.format(self.name, key, module))
			return list()
		elif toLang not in self._stringsData[module][key]:
			self._logger.error('[{}] Asked to get "{}" translation for "{}" from module "{}" but does not exist'.format(self.name, toLang, key, module))
			return list()
		else:
			return self._stringsData[module][key][toLang]


	def getStrings(self, key: str, module: str = 'system') -> list:
		return self.getTranslations(module, key, self._activeLanguage)


	def _loadSupportedLanguages(self):
		activeLangDef: str = SuperManager.getInstance().configManager.getAliceConfigByName('activeLanguage')
		langDef: dict = SuperManager.getInstance().configManager.getAliceConfigByName('supportedLanguages')

		for langCode, settings in langDef.items():
			self._supportedLanguages.append(langCode)
			if settings['default']:
				self._defaultLanguage = langCode
				self._defaultCountryCode = settings['countryCode']

			if langCode == activeLangDef:
				self._activeLanguage = langCode
				self._activeCountryCode = settings['countryCode']
				self._activeSnipsProjectId = settings['snipsProjectId']

		if not self._activeLanguage:
			if self._defaultLanguage:
				self._logger.warning('[{}] No active language defined, falling back to {}'.format(self.name, self._defaultLanguage))
				self._activeLanguage = self._defaultLanguage
				self._activeCountryCode = self._defaultCountryCode
			else:
				self._logger.warning('[{}] No active language or default language defined, falling back to "en"'.format(self.name))
				self._activeLanguage = 'en'
				self._activeCountryCode = 'US'
		else:
			self._logger.info('[{}] Active language set to "{}"'.format(self.name, self.activeLanguageAndCountryCode))

		if not self._defaultLanguage:
			if self._activeLanguage:
				self._logger.warning('[{}] No default language defined, falling back to {}'.format(self.name, self._activeLanguage))
				self._defaultLanguage = self._activeLanguage
				self._defaultCountryCode = self._activeCountryCode
			else:
				self._logger.warning('[{}] No default language or active language defined, falling back to "en"'.format(self.name))
				self._defaultLanguage = 'en'
				self._defaultCountryCode = 'US'
				self._activeLanguage = self._defaultLanguage
				self._activeCountryCode = self._defaultCountryCode
		else:
			self._logger.info('[{}] Default language set to "{}"'.format(self.name, self.activeLanguageAndCountryCode))


		if not self._activeSnipsProjectId:
			self._logger.info('[{}] No active snips project id set'.format(self.name))


	def localize(self, string: str) -> str:
		string = str(string)
		string = string.lower()

		if self._activeLanguage != 'en':
			string = str(string).lower()

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
		toLang = str(toLang).lower()

		if toLang not in self._supportedLanguages:
			raise LanguageManagerLangNotSupported

		SuperManager.getInstance().configManager.changeActiveLanguage(toLang)
		self._loadSupportedLanguages()


	def changeActiveSnipsProjectIdForLanguage(self, projectId: str, forLang: str):
		forLang = str(forLang).lower()

		if forLang not in self._supportedLanguages:
			raise LanguageManagerLangNotSupported

		SuperManager.getInstance().configManager.changeActiveSnipsProjectIdForLanguage(projectId, forLang)
		self._loadSupportedLanguages()
