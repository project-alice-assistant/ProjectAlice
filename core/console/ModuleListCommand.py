import click

@click.command(name='module:list')
@click.argument('author_name') # , help='Author\'s name'
@click.option('--full', '-f', is_flag=True, help='Display full description instead of truncated one')
def ModuleListCommand(author_name: str, full: bool):
	"""List remote modules from dedicated repository created by a AUTHOR_NAME"""

	import requests
	from terminaltables import DoubleTable
	from core.base.ModuleManager import ModuleManager

	TABLE_DATA = [['Modules created by ' + author_name]]
	table_instance = DoubleTable(TABLE_DATA)
	click.secho('\n{}\n'.format(table_instance.table), fg='yellow')

	TABLE_DATA = [['Name', 'Version', 'Langs', 'Description']]
	table_instance = DoubleTable(TABLE_DATA)

	try:
		req = requests.get('https://api.github.com/{}/{}'.format(ModuleManager.GITHUB_API_BASE_URL, author_name))

		if req.status_code == 403:
			click.secho('Github API quota limitations reached\n', err=True, bg='red')
			return
		elif req.status_code // 100 == 4:
			click.echo('> Unknown author ' + click.style(author_name, fg='red'), err=True)
			click.echo('- You can use {} to list all authors\n'.format(click.style('author:list', fg='yellow')), err=True)
			return

		for module in req.json():
			moduleInstallFile = '{0}/{1}/{2}/{2}.install'.format(ModuleManager.GITHUB_BARE_BASE_URL, author_name, module['name'])

			try:
				moduleDetails = requests.get(moduleInstallFile).json()
				tLangs = '|'.join(moduleDetails['conditions'].get('lang', ['-']))
				tDesc = moduleDetails['desc']

				if not full:
					tDesc = (tDesc[:100] + '..') if len(tDesc) > 100 else tDesc

				TABLE_DATA.append([
					moduleDetails['name'],
					moduleDetails['version'],
					tLangs,
					tDesc
				])

			except Exception:
				click.secho('Error get module {}'.format(module['name']), err=True, fg='red')
				raise

	except Exception:
		click.secho('Error listing modules', err=True, fg='red')
	else:
		click.echo(table_instance.table)