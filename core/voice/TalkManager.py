import json
import random
from pathlib import Path
from typing import Union, Callable
from functools import partial
import importlib
from inspect import getmembers, isfunction


from core.base.model.Manager import Manager


class TalkManager(Manager):

	NAME = 'TalkManager'

	def __init__(self):
		super().__init__(self.NAME)
		self._langData = dict()


	@property
	def langData(self) -> dict:
		return self._langData


	@langData.setter
	def langData(self, value: dict):
		self._langData = value


	def onStart(self):
		super().onStart()
		self.loadTalks()


	def loadTalks(self, moduleToLoad: str = None):
		# Global System Talks
		if not moduleToLoad:
			systemLangTalksMountpoint = Path('system/manager/TalkManager/talks')

			for systemLangTalkFile in systemLangTalksMountpoint.iterdir():
				lang = systemLangTalkFile.stem
				self._langData.setdefault('system', dict())[lang] = json.loads(systemLangTalkFile.read_text())

		# Module Talks
		modules = self.ConfigManager.modulesConfigurations

		for moduleName in modules:
			if moduleToLoad and moduleToLoad != moduleName:
				continue

			langTalksMountpoint = Path('modules', moduleName, 'talks')
			if not langTalksMountpoint.exists():
				continue

			self._langData[moduleName] = dict()
			for langTalkFile in langTalksMountpoint.iterdir():
				lang = langTalkFile.stem
				try:
					if langTalkFile.suffix == '.py':
						talkImport = importlib.import_module(f'modules.{moduleName}.talks.{lang}')
						mappings = dict(getmembers(talkImport, isfunction))
					else:
						mapping = json.loads(langTalkFile.read_text())

					# there can be mappings both from json and py
					if lang in self._langData[moduleName]:
						self._langData[moduleName][lang].update(mapping)
					else:
						self._langData[moduleName][lang] = mapping
				except ImportError as e:
					self.logError(f"Couldn't import talk functions {moduleName}.talks.{lang}: {e}")
					continue
				except FileNotFoundError:
					continue
				except ValueError:
					continue


	def getTexts(self, module, talk, strType='default') -> Union[list, Callable]:
		arr = list()
		try:
			module = self.Commons.toCamelCase(module)
			arr = self._langData[module][self.LanguageManager.activeLanguage][talk][strType]
		except KeyError:
			self.logWarning(f'Was asked to return unexisting texts {talk} for module {module} with type {strType}')

		return arr


	def _selectSentence(self, talkData: dict, shortReplyMode: bool) -> Union[str, Callable]:
		# when there is a mapping to a function add shortReplyMode as kwargs
		if callable(talkData):
			return partial(talkData, shortReplyMode=shortReplyMode)

		# There's no short/long version
		if isinstance(talkData, list):
			return random.choice(talkData)

		if shortReplyMode:
			try:
				return random.choice(talkData['short'])
			except KeyError:
				return random.choice(talkData['default'])
		else:
			return random.choice(talkData['default'])


	def chooseTalk(self, talk: str, module: str, activeLanguage: str, defaultLanguage: str, shortReplyMode: bool) -> Union[str, Callable]:
		try:
			talkData = self._langData[module][activeLanguage][talk]
			return self._selectSentence(talkData, shortReplyMode=shortReplyMode)
		except KeyError:
			# Fallback to default language then
			if activeLanguage != defaultLanguage:
				self.logError(f'Was asked to get "{talk}" from "{module}" module in "{activeLanguage}" but it doesn\'t exist, falling back to "{defaultLanguage}" version instead')
				# call itself again with default language and then exit because activeLanguage == defaultLanguage
				return self.chooseTalk(talk, module, defaultLanguage, defaultLanguage, shortReplyMode)

			# Give up, that text does not exist...
			self.logError(f'Was asked to get "{talk}" from "{module}" module but language string doesn\'t exist')
			return ''


	def randomTalk(self, talk: str, module: str = '', forceShortTalk: bool = False) -> str:
		"""
		Gets a random string to speak corresponding to talk string. If no module provided it will use the caller's name
		:param talk:
		:param module:
		:param forceShortTalk:
		:return:
		"""
		module = module or self.getFunctionCaller()
		if not module:
			return ''

		shortReplyMode = forceShortTalk or self.UserManager.checkIfAllUser('sleeping') or self.ConfigManager.getAliceConfigByName('shortReplies')
		activeLanguage = self.LanguageManager.activeLanguage
		defaultLanguage = self.LanguageManager.defaultLanguage

		string = self.chooseTalk(talk, module, activeLanguage, defaultLanguage, shortReplyMode)
		if not string:
			return ''


		if self.ConfigManager.getAliceConfigByName('whisperWhenSleeping') and \
			self.TTSManager.tts.getWhisperMarkup() and \
			self.UserManager.checkIfAllUser('sleeping'):

			start, end = self.TTSManager.tts.getWhisperMarkup()
			string = f'{start}{string}{end}'

		return string
