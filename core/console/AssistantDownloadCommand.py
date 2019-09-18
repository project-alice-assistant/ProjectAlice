from terminaltables import DoubleTable
import click

from core.base.ModuleManager import ModuleManager
from core.dialog.ProtectedIntentManager import ProtectedIntentManager
from core.snips.SnipsConsoleManager import SnipsConsoleManager
from core.user.UserManager import UserManager
from core.util.DatabaseManager import DatabaseManager
from core.util.ThreadManager import ThreadManager
from core.voice.LanguageManager import LanguageManager

@click.command(name='assistant:download')
def AssistantDownloadCommand():
	"""Download assistant"""
	TABLE_DATA = [['Assistant Downloader']]
	table_instance = DoubleTable(TABLE_DATA)
	click.secho('\n{}\n'.format(table_instance.table), fg='green')

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

	click.echo('It may take some time...')
	snipsConsoleManager.download(languageManager.activeSnipsProjectId)

	click.echo('\n\nAssistant {}\n'.format(click.style('downloaded!', fg='green')))
