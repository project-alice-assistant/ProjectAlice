from terminaltables import DoubleTable
import click

from core.snips.SamkillaManager import SamkillaManager
from core.snips.SnipsConsoleManager import SnipsConsoleManager
from core.util.ThreadManager import ThreadManager
from core.voice.LanguageManager import LanguageManager

@click.command(name='assistant:sync')
@click.option('--download', '-d', is_flag=True, help='Also download the new trained assistant')
def AssistantSyncCommand(download: bool):
	"""Sync dialog templates for all modules"""

	TABLE_DATA = [['Assistant Dialog Templates Sync']]
	table_instance = DoubleTable(TABLE_DATA)
	click.secho('\n{}\n'.format(table_instance.table), fg='green')

	languageManager = LanguageManager()
	languageManager.onStart()

	threadManager = ThreadManager()
	threadManager.onStart()

	snipsConsoleManager = SnipsConsoleManager()
	snipsConsoleManager.onStart()

	samkillaManager = SamkillaManager()

	self.write('It may take some time...\n')
	changes = samkillaManager.sync(download=False)

	if changes:
		click.echo('There are {}'.format(click.style('changes', fg='green')))
	else:
		click.echo('There are no {}'.format(click.style('changed', fg='red')))


	click.echo('\nAll dialog templates {}\n'.format(click.style('synced!', fg='green')))

	if download:
		snipsConsoleManager.download(languageManager.activeSnipsProjectId)
		click.echo('Downloading assistant...\nAssistant {}\n'.format(click.style('downloaded!', fg='green')))