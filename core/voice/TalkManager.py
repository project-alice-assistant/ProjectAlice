# -*- coding: utf-8 -*-
import json
import os
import random

from core.commons import commons
import core.base.Managers as managers
from core.base.Manager import Manager


class TalkManager(Manager):

	NAME = 'TalkManager'

	def __init__(self, mainClass):
		super().__init__(mainClass, self.NAME)

		managers.TalkManager = self
		self._langData = dict()


	@property
	def langData(self) -> dict:
		return self._langData


	def onStart(self):
		super().onStart()
		self.loadTalks()


	def loadTalks(self, moduleToLoad: str = None):
		# Global System Talks
		if not moduleToLoad:
			systemLangTalksMountpoint = 'system/manager/TalkManager/talks'

			for systemLangTalkFile in os.listdir(systemLangTalksMountpoint):
				lang = systemLangTalkFile.replace('.json', '')

				with open('{}/{}'.format(systemLangTalksMountpoint, systemLangTalkFile)) as jsonFile:
					if "system" not in self._langData:
						self._langData["system"] = dict()

					self._langData["system"][lang] = json.load(jsonFile)

		# Module Talks
		modules = managers.ModuleManager.getModules()

		for module in modules.values():
			moduleName = module['instance'].name
			if moduleToLoad and moduleToLoad != moduleName:
				continue

			langTalksMountpoint = 'modules/{}/talks'.format(moduleName)

			for langTalkFile in os.listdir(langTalksMountpoint):
				lang = langTalkFile.replace('.json', '')

				try:
					with open('{}/{}'.format(langTalksMountpoint, langTalkFile)) as jsonFile:
						if moduleName not in self._langData:
							self._langData[moduleName] = dict()

						self._langData[moduleName][lang] = json.load(jsonFile)
				except FileNotFoundError:
					continue
				except ValueError:
					continue


	def getTexts(self, module, talk, strType = 'default') -> list:
		arr = list()
		try:
			module = commons.toCamelCase(module)
			arr = self._langData[module][managers.LanguageManager.activeLanguage][talk][strType]
		except KeyError:
			self._logger.warning('Was asked to return unexisting texts {} for module {} with type {}'.format(talk, module, strType))

		return arr


	def randomTalk(self, talk: str, module: str = '', forceShortTalk: bool = False) -> str:
		"""
		Gets a random string to speak corresponding to talk string. If no module provided it will use the caller's name
		:param talk:
		:param module:
		:param forceShortTalk:
		:return:
		"""

		if not module:
			module = self.getFunctionCaller()
			if not module:
				return ''

		shortReplyMode = forceShortTalk or managers.UserManager.checkIfAllUser('sleeping') or managers.ConfigManager.getAliceConfigByName('shortReplies')
		activeLanguage = managers.LanguageManager.activeLanguage
		defaultLanguage = managers.LanguageManager.defaultLanguage

		try:
			# Try to find the string needed
			if shortReplyMode:
				string = random.choice(self._langData[module][activeLanguage][talk]['short'])
			else:
				string = random.choice(self._langData[module][activeLanguage][talk]['default'])
		except Exception:
			try:
				# Maybe there's only a default version?
				string = random.choice(self._langData[module][activeLanguage][talk]['default'])
			except Exception:
				try:
					# Maybe there's no short/long version?
					string = random.choice(self._langData[module][activeLanguage][talk])
				except Exception:
					try:
						# Fallback to default language then
						if activeLanguage == defaultLanguage:
							raise Exception

						self._logger.error('Was asked to get "{}" from "{}" module in "{}" but it doesn\'t exist, falling back to "{}" version instead'.format(talk, module, activeLanguage, defaultLanguage))
						string = random.choice(self._langData[module][defaultLanguage][talk])
					except Exception:
						# Give up, that text does not exist...
						self._logger.error('Was asked to get "{}" from "{}" module but language string doesn\'t exist'.format(talk, module))
						return ''

		if managers.ConfigManager.getAliceConfigByName('tts') == 'amazon' and \
			managers.ConfigManager.getAliceConfigByName('whisperWhenSleeping') and \
			managers.UserManager.checkIfAllUser('sleeping') and \
			len(managers.UserManager.getAllUserNames()) > 0:
			string = '<amazon:effect name="whispered">{}</amazon:effect>'.format(string)

		return u'{0}'.format(string)
