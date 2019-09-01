# -*- coding: utf-8 -*-

from terminaltables import DoubleTable

from core.base.ConfigManager import ConfigManager
from core.base.ModuleManager import ModuleManager
from core.console.Command import Command
from core.console.input.InputArgument import InputArgument
from core.console.input.InputOption import InputOption
from core.dialog.ProtectedIntentManager import ProtectedIntentManager
from core.snips.SamkillaManager import SamkillaManager
from core.snips.SnipsConsoleManager import SnipsConsoleManager
from core.user.UserManager import UserManager
from core.util.DatabaseManager import DatabaseManager
from core.util.ThreadManager import ThreadManager
from core.voice.LanguageManager import LanguageManager


#
# ModuleIntentListCommand list modules from dedicated repository
#
class ModuleIntentListCommand(Command):

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
		self.setName('module:intent:list')
		self.setDescription('List intents and utterances for a given module')
		self.setDefinition([
			InputArgument(name='moduleName', mode=InputArgument.REQUIRED, description='Module\'s name'),
			InputOption(name='--full', shortcut='-f', mode=InputOption.VALUE_NONE, description='Display full description instead of truncated one'),
			InputOption(name='--intent', shortcut='-i', mode=InputOption.VALUE_OPTIONAL, description='Show more data about specific intent'),
		])
		self.setHelp('> The %command.name% list intents and utterances for a given module:\n'
					 '  <fg:magenta>%command.full_name%<fg:reset> <fg:cyan>moduleName<fg:reset> <fg:yellow>[-f|--full]<fg:reset> <fg:yellow>[-i|--intent=intentName]<fg:reset>')

	def execute(self, inputt):
		TABLE_DATA = [['Intents of module ' + inputt.getArgument('moduleName')]]
		table_instance = DoubleTable(TABLE_DATA)
		self.write('\n' + table_instance.table + '\n', 'yellow')

		if inputt.getOption('intent'):
			return self.intentMode(inputt)

		return self.moduleMode(inputt)


	def intentMode(self, inputt):
		TABLE_DATA = [['Utterances']]
		table_instance = DoubleTable(TABLE_DATA)

		intentFound = False

		for dtIntentName, dtModuleName in self._intentNameSkillMatching.items():
			if dtIntentName == inputt.getOption('intent'):
				intentFound = True

				for utterance, _ in self._intentsModulesValues[dtIntentName]['utterances'].items():
					tDesc = utterance

					if not inputt.getOption('full'):
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

	def moduleMode(self, inputt):
		TABLE_DATA = [['Intent', 'Description']]
		table_instance = DoubleTable(TABLE_DATA)

		moduleFound = False

		for dtIntentName, dtModuleName in self._intentNameSkillMatching.items():
			if dtModuleName == inputt.getArgument('moduleName'):
				moduleFound = True
				tDesc = self._intentsModulesValues[dtIntentName]['__otherattributes__']['description']

				if not inputt.getOption('full'):
					tDesc = (tDesc[:self.DESCRIPTION_MAX] + '..') if len(tDesc) > self.DESCRIPTION_MAX else tDesc

				TABLE_DATA.append([
					dtIntentName,
					'-' if len(tDesc) == 0 else tDesc
				])

		if not moduleFound:
			self.nl()
			self.write('No intent found')
			self.nl()
			return

		self.write(table_instance.table)
