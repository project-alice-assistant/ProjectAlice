import click

@click.command(name='assistant:sync')
@click.option('--download', '-d', is_flag=True, help='Also download the new trained assistant')
def AssistantSyncCommand(download: bool):
	"""Sync dialog templates for all modules"""

	from terminaltables import DoubleTable
	from core.base.SuperManager import SuperManager

	TABLE_DATA = [['Assistant Dialog Templates Sync']]
	table_instance = DoubleTable(TABLE_DATA)
	click.secho('\n{}\n'.format(table_instance.table), fg='green')

	superManager = SuperManager(None)
	superManager.initManagers()
	superManager.onStart()

	snipsConsoleManager = superManager.getManager('SnipsConsoleManager')
	samkillaManager = superManager.getManager('SamkillaManager')
	languageManager = superManager.getManager('LanguageManager')

	click.echo('It may take some time...\n')
	changes = samkillaManager.sync(download=False)
	if changes:
		click.echo('There are {}'.format(click.style('changes', fg='green')))
	else:
		click.echo('There are no {}'.format(click.style('changes', fg='red')))


	click.echo('\nAll dialog templates {}\n'.format(click.style('synced!', fg='green')))

	if download:
		snipsConsoleManager.download(languageManager.activeSnipsProjectId)
		click.echo('Downloading assistant...\nAssistant {}\n'.format(click.style('downloaded!', fg='green')))