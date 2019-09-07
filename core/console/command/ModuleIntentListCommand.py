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
from core.util.InternetManager import InternetManager
from core.util.TelemetryManager import TelemetryManager
from core.util.ThreadManager import ThreadManager
from core.voice.LanguageManager import LanguageManager


#
# ModuleIntentListCommand list modules from dedicated repository
#
class ModuleIntentListCommand(Command):
	DESCRIPTION_MAX = 100


	def __init__(self):
		super().__init__()

		configManager = ConfigManager()
		configManager.onStart()

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

		internetManager = InternetManager()
		internetManager.onStart()

		telemetryManager = TelemetryManager()
		telemetryManager.onStart()

		moduleManager = ModuleManager()
		moduleManager.onStart()

		snipsConsoleManager = SnipsConsoleManager()
		snipsConsoleManager.onStart()

		samkillaManager = SamkillaManager()

		self._slotTypesModulesValues, self._intentsModulesValues, self._intentNameSkillMatching = samkillaManager.getDialogTemplatesMaps(
			runOnAssistantId=languageManager.activeSnipsProjectId,
			languageFilter=languageManager.activeLanguage
		)


	def create(self):
		self.name = 'module:intent:list'
		self.setDescription('List intents and utterances for a given module')
		self.setDefinition([
			InputArgument(name='moduleName', mode=InputArgument.Mode.REQUIRED, description='Module\'s name'),
			InputOption(name='--full', shortcut='-f', mode=InputOption.Mode.NONE, description='Display full description instead of truncated one'),
			InputOption(name='--intent', shortcut='-i', mode=InputOption.Mode.OPTIONAL, description='Show more data about specific intent'),
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
						'-' if not tDesc else tDesc
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
					'-' if not tDesc else tDesc
				])

		if not moduleFound:
			self.nl()
			self.write('No intent found')
			self.nl()
			return

		self.write(table_instance.table)
