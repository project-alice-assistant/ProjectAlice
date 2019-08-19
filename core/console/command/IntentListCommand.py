# -*- coding: utf-8 -*-

import json
import os
import requests
import random

from terminaltables import DoubleTable

from core.console.Command import Command
from core.console.input.InputArgument import InputArgument
from core.console.input.InputOption import InputOption
from core.snips.SamkillaManager import SamkillaManager
from core.base.ModuleManager import ModuleManager
from core.snips.SnipsConsoleManager import SnipsConsoleManager
from core.voice.LanguageManager import LanguageManager
from core.util.ThreadManager import ThreadManager
from core.util.DatabaseManager import DatabaseManager
from core.dialog.ProtectedIntentManager import ProtectedIntentManager
from core.base.ConfigManager import ConfigManager
from core.user.UserManager import UserManager
from core.base.model.GithubCloner import GithubCloner

#
# IntentListCommand list modules from dedicated repository
#
class IntentListCommand(Command):

	DESCRIPTION_MAX = 100

	def __init__(self):
		super().__init__()

		configManager = ConfigManager(self)
		configManager.onStart()

		languageManager = LanguageManager(self)
		languageManager.onStart()

		threadManager = ThreadManager(self)
		threadManager.onStart()

		protectedIntentManager = ProtectedIntentManager(self)
		protectedIntentManager.onStart()

		databaseManager = DatabaseManager(self)
		databaseManager.onStart()

		userManager = UserManager(self)
		userManager.onStart()

		moduleManager = ModuleManager(self)
		moduleManager.onStart()

		snipsConsoleManager = SnipsConsoleManager(self)
		snipsConsoleManager.onStart()

		samkillaManager = SamkillaManager(self)

		self._slotTypesModulesValues, self._intentsModulesValues, self._intentNameSkillMatching = samkillaManager.getDialogTemplatesMaps(
			runOnAssistantId=languageManager.activeSnipsProjectId,
			languageFilter=languageManager.activeLanguage
		)

	def create(self):
		self.setName('intent:list')
		self.setDescription('List intents and utterances for a given module')
		self.setDefinition([
			InputOption(name='--module', shortcut='-m', mode=InputOption.VALUE_OPTIONAL, description='Show more data about specific module'),
			InputOption(name='--full', shortcut='-f', mode=InputOption.VALUE_OPTIONAL, description='Display full description instead of truncated one'),
			InputOption(name='--intent', shortcut='-i', mode=InputOption.VALUE_OPTIONAL, description='Show more data about specific intent'),
		])
		self.setHelp('> The %command.name% list intents and utterances:\n'
					 '  <fg:magenta>%command.full_name%<fg:reset> <fg:yellow>[-m|--module]<fg:reset> <fg:yellow>[-f|--full]<fg:reset> <fg:yellow>[-i|--intent=intentName]<fg:reset>')

	def execute(self, input):
		if input.getOption('intent'):
			return self.intentMode(input)

		if input.getOption('module'):
			return self.moduleMode(input)

		return self.allMode(input)


	def allMode(self, input):
		TABLE_DATA = [['All Alice intents']]
		table_instance = DoubleTable(TABLE_DATA)
		self.write('\n' + table_instance.table + '\n', 'yellow')

		TABLE_DATA = [['Intent', 'D', 'Description', 'Example']]
		table_instance = DoubleTable(TABLE_DATA)
		table_instance.justify_columns[1] = 'center'


		for dtIntentName, dtModuleName in self._intentNameSkillMatching.items():
			tDesc = self._intentsModulesValues[dtIntentName]['__otherattributes__']['description']
			tEnabledByDefault = self._intentsModulesValues[dtIntentName]['__otherattributes__']['enabledByDefault']

			tUtterance, _ = random.choice(list(self._intentsModulesValues[dtIntentName]['utterances'].items()))

			if not input.getOption('full'):
				tDesc = (tDesc[:self.DESCRIPTION_MAX] + '..') if len(tDesc) > self.DESCRIPTION_MAX else tDesc
				tUtterance = (tUtterance[:self.DESCRIPTION_MAX] + '..') if len(tUtterance) > self.DESCRIPTION_MAX else tUtterance


			TABLE_DATA.append([
				dtIntentName,
				'X' if tEnabledByDefault else '',
				'-' if len(tDesc) == 0 else tDesc,
				'-' if len(tUtterance) == 0 else tUtterance
			])

		self.write(table_instance.table)


	def intentMode(self, input):
		TABLE_DATA = [['Utterances of ' + input.getOption('intent') + ' intent']]
		table_instance = DoubleTable(TABLE_DATA)
		self.write('\n' + table_instance.table + '\n', 'yellow')

		TABLE_DATA = [['Utterances']]
		table_instance = DoubleTable(TABLE_DATA)

		intentFound = False

		for dtIntentName, dtModuleName in self._intentNameSkillMatching.items():
			if dtIntentName == input.getOption('intent') and dtModuleName == input.getOption('module'):
				intentFound = True

				for utterance, _ in self._intentsModulesValues[dtIntentName]['utterances'].items():
					tDesc = utterance

					if not input.getOption('full'):
						tDesc = (tDesc[:self.DESCRIPTION_MAX] + '..') if len(tDesc) > self.DESCRIPTION_MAX else tDesc

					TABLE_DATA.append([
						'-' if len(tDesc) == 0 else tDesc
					])

		if not intentFound:
			self.nl()
			self.write('No intent found')
			self.nl()
			return

		self.write(table_instance.table)

	def moduleMode(self, input):
		TABLE_DATA = [['Intents of ' + input.getOption('module') + ' module']]
		table_instance = DoubleTable(TABLE_DATA)
		self.write('\n' + table_instance.table + '\n', 'yellow')

		TABLE_DATA = [['Intent', 'Description', 'Default']]
		table_instance = DoubleTable(TABLE_DATA)

		moduleFound = False

		for dtIntentName, dtModuleName in self._intentNameSkillMatching.items():
			if dtModuleName == input.getOption('module'):
				moduleFound = True
				tDesc = self._intentsModulesValues[dtIntentName]['__otherattributes__']['description']
				tEnabledByDefault = self._intentsModulesValues[dtIntentName]['__otherattributes__']['enabledByDefault']

				if not input.getOption('full'):
					tDesc = (tDesc[:self.DESCRIPTION_MAX] + '..') if len(tDesc) > self.DESCRIPTION_MAX else tDesc

				TABLE_DATA.append([
					dtIntentName,
					'-' if len(tDesc) == 0 else tDesc,
					'X' if tEnabledByDefault else ''
				])

		if not moduleFound:
			self.nl()
			self.write('No intent found')
			self.nl()
			return

		self.write(table_instance.table)
