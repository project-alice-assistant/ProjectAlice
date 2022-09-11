#  Copyright (c) 2021
#
#  This file, TalkManager.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:48 CEST

import json
import random
from pathlib import Path

from core.base.model.Manager import Manager


class TalkManager(Manager):

	def __init__(self):
		super().__init__()
		self._langData = dict()


	@property
	def langData(self) -> dict:
		return self._langData


	def onStart(self):
		super().onStart()
		self.loadSystemTalks()


	def loadSystemTalks(self):
		systemLangTalksMountpoint = Path('system/manager/TalkManager/talks')

		for systemLangTalkFile in systemLangTalksMountpoint.glob('*.json'):
			lang = systemLangTalkFile.stem
			self._langData.setdefault('system', dict())[lang] = json.loads(systemLangTalkFile.read_text())


	def loadSkillTalks(self, skillName: str):
		skillInstance = self.SkillManager.getSkillInstance(skillName)
		if not skillInstance:
			self.logError(f'Loading talks for skill **{skillName}** failed')

		try:
			skillTalks = skillInstance.getResource(f'talks/{self.LanguageManager.activeLanguageAndCountryCode}.json')
			if not skillTalks.exists():
				skillTalks = skillInstance.getResource(f'talks/{self.LanguageManager.activeLanguage}.json')

			self._langData.setdefault(skillName, dict())[self.LanguageManager.activeLanguage] = json.loads(skillTalks.read_text())
		except FileNotFoundError:
			self.logDebug(f'Talk file for skill **{skillName}** does not exist')
		except ValueError:
			self.logError(f'Talk file for skill **{skillName}** is corrupted')


	def getTexts(self, skill, talk, strType='default') -> list:
		arr = list()
		try:
			skill = self.Commons.toCamelCase(skill)
			arr = self._langData[skill][self.LanguageManager.activeLanguage][talk][strType]
		except KeyError:
			self.logWarning(f'Was asked to return unexisting texts {talk} for skill {skill} with type {strType}')

		return arr


	def chooseTalk(self, talk: str, skill: str, activeLanguage: str, defaultLanguage: str, shortReplyMode: bool) -> str:
		try:
			talkData = self._langData[skill][activeLanguage][talk]

			# There's no short/long version?
			if isinstance(talkData, list):
				return random.choice(self._langData[skill][activeLanguage][talk])

			if shortReplyMode:
				try:
					return random.choice(talkData['short'])
				except KeyError:
					return random.choice(talkData['default'])
			else:
				return random.choice(talkData['default'])
		except KeyError:
			# Fallback to default language then
			if activeLanguage != defaultLanguage:
				self.logError(f'Was asked to get **{talk}** from **{skill}** skill in **{activeLanguage}** but it doesn\'t exist, falling back to **{defaultLanguage}** version instead', printStack=False)
				# call itself again with default language and then exit because activeLanguage == defaultLanguage
				return self.chooseTalk(talk, skill, defaultLanguage, defaultLanguage, shortReplyMode)

			# Give up, that text does not exist...
			self.logError(f'Was asked to get **{talk}** from **{skill}** skill but language string doesn\'t exist', printStack=False)
			return ''


	def randomTalk(self, talk: str, skill: str = '', forceShortTalk: bool = False) -> str:
		"""
		Gets a random string to speak corresponding to talk string. If no skill provided it will use the caller's name
		:param talk:
		:param skill:
		:param forceShortTalk:
		:return:
		"""
		skill = skill or self.getFunctionCaller()
		if not skill:
			return ''

		shortReplyMode = forceShortTalk or self.UserManager.checkIfAllUser('sleeping') or self.ConfigManager.getAliceConfigByName('shortReplies')
		activeLanguage = self.LanguageManager.activeLanguage
		defaultLanguage = self.LanguageManager.defaultLanguage

		string = self.chooseTalk(talk, skill, activeLanguage, defaultLanguage, shortReplyMode)
		if not string:
			return ''

		if self.ConfigManager.getAliceConfigByName('whisperWhenSleeping') and \
				self.TTSManager.tts.getWhisperMarkup() and \
				self.UserManager.checkIfAllUser('sleeping'):

			start, end = self.TTSManager.tts.getWhisperMarkup()
			string = f'{start}{string}{end}'

		return string
