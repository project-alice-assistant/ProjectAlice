from terminaltables import DoubleTable

from core.base.ModuleManager import ModuleManager
from core.console.Command import Command
from core.dialog.ProtectedIntentManager import ProtectedIntentManager
from core.snips.SnipsConsoleManager import SnipsConsoleManager
from core.user.UserManager import UserManager
from core.util.DatabaseManager import DatabaseManager
from core.util.ThreadManager import ThreadManager
from core.voice.LanguageManager import LanguageManager


#
# AssistantDownloadCommand download the assistant
#
class AssistantDownloadCommand(Command):

	def create(self):
		self.name = 'assistant:download'
		self.setDescription('Download assistant')
		self.setDefinition()
		self.setHelp('> The %command.name% command download the assistant from snips console:\n'
					 '  <fg:magenta>%command.full_name%<fg:reset>')


	def execute(self, inputt):
		TABLE_DATA = [['Assistant Downloader']]
		table_instance = DoubleTable(TABLE_DATA)
		self.write('\n' + table_instance.table + '\n', 'green')

		languageManager = LanguageManager()
		languageManager.onStart()

		threadManager = ThreadManager()
		threadManager.onStart()

		protectedIntentManager = ProtectedIntentManager()
		protectedIntentManager.onStart()

		databaseManager = DatabaseManager()
		databaseManager.onStart()

		userManager = UserManager()
		userManager.onStart()

		moduleManager = ModuleManager()
		moduleManager.onStart()

		snipsConsoleManager = SnipsConsoleManager()
		snipsConsoleManager.onStart()

		self.write('It may take some time...')
		snipsConsoleManager.download(languageManager.activeSnipsProjectId)

		self.nl()
		self.nl()
		self.write('Assistant <fg:green>downloaded!<fg:reset>')
		self.nl()
