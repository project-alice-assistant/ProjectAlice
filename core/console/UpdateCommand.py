import click
from terminaltables import DoubleTable # type: ignore
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
	click.secho(f'\n{table_instance.table}\n', fg='green')

	superManager = SuperManager(None)
	superManager.initManagers()
	superManager.onStart()

	snipsConsoleManager = superManager.getManager('SnipsConsoleManager')
	languageManager = superManager.getManager('LanguageManager')

	downloaded = snipsConsoleManager.download(languageManager.activeSnipsProjectId)

	if downloaded:
		click.echo(f"\n\nAssistant {click.style('downloaded!', fg='green')}\n")
	else:
		click.echo(f"\n\nAssistant {click.style('download failed', fg='red')}\n", err=True)