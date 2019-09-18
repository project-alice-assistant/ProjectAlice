import click

@click.command(name='author:list')
def AuthorListCommand():
	"""List authors from dedicated repository"""

	import requests
	from terminaltables import DoubleTable
	from core.base.ModuleManager import ModuleManager
	
	TABLE_DATA = [['Authors List']]
	table_instance = DoubleTable(TABLE_DATA)
	click.secho('\n{}\n'.format(table_instance.table), fg='magenta')

	TABLE_DATA = [['Name']]
	table_instance = DoubleTable(TABLE_DATA)

	try:
		req = requests.get('https://api.github.com/{}'.format(ModuleManager.GITHUB_API_BASE_URL))

		if req.status_code == 403:
			click.secho('Github API quota limitations reached\n', err=True, bg='red')
			return

		for author in req.json():
			TABLE_DATA.append([
				author['name'],
			])

	except Exception:
		click.secho('Error listing authors', err=True, fg='red')
	else:
		click.echo(table_instance.table)