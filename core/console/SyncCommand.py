import click
import logging.handlers
from core.base.SuperManager import SuperManager

@click.group()
def Sync():
	"""Sync components of alice"""
	pass

@Sync.command()
@click.option('--download', '-d', is_flag=True, help='Download the assistant after syncing')
def assistant(download: bool):
	"""Sync dialog templates for all skills"""

	_logger = logging.getLogger('ProjectAlice')
	_logger.setLevel(logging.INFO)
	_logger.addHandler(logging.StreamHandler())

	superManager = SuperManager(None)
	superManager.initManagers()
	superManager.onStart()

	samkillaManager = superManager.getManager('SamkillaManager')
	snipsConsoleManager = superManager.getManager('SnipsConsoleManager')
	languageManager = superManager.getManager('LanguageManager')

	try:
		samkillaManager.sync(download=False)
	except Exception as e:
		click.echo(f'Failed syncing with remote snips console: {e}', err=True)
		return

	if download:
		downloaded = snipsConsoleManager.download(languageManager.activeSnipsProjectId)

		if downloaded:
			click.echo(f"\n\nAssistant {click.style('downloaded!', fg='green')}\n")
		else:
			click.echo(f"\n\nAssistant {click.style('download failed', fg='red')}\n", err=True)
