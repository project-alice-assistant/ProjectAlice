import click
import urllib.request
import requests
from terminaltables import DoubleTable
from core.base.ModuleManager import ModuleManager

@click.group()
def module():
	"""Module related commands"""
	pass


@module.command()
@click.argument('author_name')
@click.argument('module_name')
def install(author_name: str, module_name: str):
	"""Download and install module from dedicated repository"""

	TABLE_DATA = [['Module Installer']]
	table_instance = DoubleTable(TABLE_DATA)
	click.secho('\n{}\n'.format(table_instance.table), fg='yellow')

	try:
		url = '{0}/{1}/{2}/{2}.install'.format(ModuleManager.GITHUB_BARE_BASE_URL, author_name, module_name)
		req = requests.get(url)

		if req.status_code // 100 == 4:
			click.echo(
				'> Unknown {} pair\n'.format(click.style('{}/{}'.format(author_name, module_name), fg='red'))
				+ '- You can use {} to list all authors\n'.format(click.style('author:list', fg='yellow'))
				+ '- You can use {} to list all modules from an author\n\n'.format(click.style('module:list', fg='yellow')),
				err=True
			)
			return

		module = req.json()
		click.echo(
			'+ Informations:\n'
			+ '===============\n'
			+ 'name: {}\n'.format(click.style(str(module['name']), fg='yellow'))
			+ 'version: {}\n'.format(click.style(str(module['version']), fg='yellow'))
			+ 'author: {}\n'.format(click.style(module['author'], fg='yellow'))
			+ 'maintainers: {}\n'.format(click.style(', '.join(module['maintainers']), fg='yellow'))
			+ 'description: {}\n'.format(click.style(module['desc'], fg='yellow'))
			+ 'aliceMinVersion: {}\n'.format(click.style(module['aliceMinVersion'], fg='yellow'))
			+ 'pip requirements: {}\n'.format(click.style(', '.join(module['pipRequirements']), fg='yellow'))
			+ 'system requirements: {}\n\n'.format(click.style(', '.join(module['systemRequirements']), fg='yellow'))
			+ '+ Conditions:\n'
			+ '=============\n'
			+ 'lang: {}\n\n'.format(click.style(', '.join(module['conditions']['lang']), fg='yellow'))
		)

		urllib.request.urlretrieve(url, 'system/moduleInstallTickets/{}.install'.format(module_name))

	except Exception as e:
		click.secho('Error listing authors', err=True, fg='red')


@module.command(name='list')
@click.argument('author_name') # , help='Author\'s name'
@click.option('--full', '-f', is_flag=True, help='Display full description instead of truncated one')
def moduleList(author_name: str, full: bool):
	"""List remote modules from dedicated repository created by a AUTHOR_NAME"""

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