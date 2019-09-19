import click
from terminaltables import DoubleTable
from core.base.SuperManager import SuperManager

@click.group()
def assistant():
	pass


@assistant.command()
def download():
	"""Download assistant"""

	TABLE_DATA = [['Assistant Downloader']]
	table_instance = DoubleTable(TABLE_DATA)
	click.secho('\n{}\n'.format(table_instance.table), fg='green')

	superManager = SuperManager(None)
	superManager.initManagers()

	snipsConsoleManager = superManager.getManager('SnipsConsoleManager')
	snipsConsoleManager.onStart()
	languageManager = superManager.getManager('LanguageManager')
	languageManager.onStart()

	click.echo('It may take some time...')
	if snipsConsoleManager.download(languageManager.activeSnipsProjectId):
		click.echo('\n\nAssistant {}\n'.format(click.style('downloaded!', fg='green')))
	else:
		click.echo('\n\nAssistant {}\n'.format(click.style('download failed!', fg='red')), err=True)


@assistant.command()
@click.option('--download', '-d', is_flag=True, help='Also download the new trained assistant')
def sync(download: bool):
	"""Sync dialog templates for all modules"""

	TABLE_DATA = [['Assistant Dialog Templates Sync']]
	table_instance = DoubleTable(TABLE_DATA)
	click.secho('\n{}\n'.format(table_instance.table), fg='green')

	superManager = SuperManager(None)
	superManager.initManagers()

	snipsConsoleManager = superManager.getManager('SnipsConsoleManager')
	snipsConsoleManager.onStart()
	samkillaManager = superManager.getManager('SamkillaManager')
	samkillaManager.onStart()
	languageManager = superManager.getManager('LanguageManager')
	languageManager.onStart()

	click.echo('It may take some time...\n')
	changes = False
	try:
		changes = samkillaManager.sync(download=False)
	except Exception as e:
		print(e)

	if changes:
		click.echo('There are {}'.format(click.style('changes', fg='green')))
	else:
		click.echo('There are no {}'.format(click.style('changes', fg='red')))


	click.echo('\nAll dialog templates {}\n'.format(click.style('synced!', fg='green')))

	if download:
		click.echo('Downloading assistant which may take some time...')
		if snipsConsoleManager.download(languageManager.activeSnipsProjectId):
			click.echo('\n\nAssistant {}\n'.format(click.style('downloaded!', fg='green')))
		else:
			click.echo('\n\nAssistant {}\n'.format(click.style('download failed!', fg='red')), err=True)
