import click

@click.command(name='assistant:download')
def AssistantDownloadCommand():
	"""Download assistant"""

	from terminaltables import DoubleTable
	from core.base.SuperManager import SuperManager

	TABLE_DATA = [['Assistant Downloader']]
	table_instance = DoubleTable(TABLE_DATA)
	click.secho('\n{}\n'.format(table_instance.table), fg='green')

	superManager = SuperManager(None)
	superManager.initManagers()
	superManager.onStart()

	snipsConsoleManager = superManager.getManager('SnipsConsoleManager')
	languageManager = superManager.getManager('LanguageManager')

	click.echo('It may take some time...')
	if snipsConsoleManager.download(languageManager.activeSnipsProjectId):
		click.echo('\n\nAssistant {}\n'.format(click.style('downloaded!', fg='green')))
	else:
		click.echo('\n\nAssistant {}\n'.format(click.style('download failed!', fg='red')), err=True)
