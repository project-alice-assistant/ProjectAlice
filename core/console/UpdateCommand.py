import click
from terminaltables import DoubleTable
from core.base.SuperManager import SuperManager
import logging.handlers

@click.group()
def Update():
	"""update components of alice"""
	pass


@Update.command()
def assistant():
	"""Update the voice assistant by retraining"""

	_logger = logging.getLogger('ProjectAlice')
	_logger.setLevel(logging.INFO)
	_logger.addHandler(logging.StreamHandler())
	
	TABLE_DATA = [['Assistant Downloader']]
	table_instance = DoubleTable(TABLE_DATA)
	click.secho('\n{}\n'.format(table_instance.table), fg='green')

	superManager = SuperManager(None)
	superManager.initManagers()

	snipsConsoleManager = superManager.getManager('SnipsConsoleManager')
	snipsConsoleManager.onStart()
	languageManager = superManager.getManager('LanguageManager')
	languageManager.onStart()

	downloaded = snipsConsoleManager.download(languageManager.activeSnipsProjectId)

	if downloaded:
		click.echo('\n\nAssistant {}\n'.format(click.style('downloaded!', fg='green')))
	else:
		click.echo('\n\nAssistant {}\n'.format(click.style('download failed', fg='red')), err=True)