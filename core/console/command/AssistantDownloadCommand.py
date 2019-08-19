# -*- coding: utf-8 -*-

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
from core.user.UserManager import UserManager

#
# AssistantDownloadCommand download the assistant
#
class AssistantDownloadCommand(Command):

	def create(self):
		self.setName('assistant:download')
		self.setDescription('Download assistant')
		self.setDefinition()
		self.setHelp('> The %command.name% command download the assistant from snips console:\n'
					 '  <fg:magenta>%command.full_name%<fg:reset>')

	def execute(self, input):
		TABLE_DATA = [['Assistant Downloader']]
		table_instance = DoubleTable(TABLE_DATA)
		self.write('\n' + table_instance.table + '\n', 'green')

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

		self.write('It may take some time...')
		snipsConsoleManager._download(languageManager.activeSnipsProjectId)

		self.nl()
		self.nl()
		self.write('Assistant <fg:green>downloaded!<fg:reset>')
		self.nl()



