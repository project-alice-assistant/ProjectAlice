import click
import urllib.request
import requests
from terminaltables import DoubleTable
from core.base.ModuleManager import ModuleManager

@click.group()
def Add():
	"""Add new components to alice"""
	pass


@Add.command()
@click.argument('author_name')
@click.argument('module_name')
def module(author_name: str, module_name: str):
	"""Add module from dedicated repository to Alice"""

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
			+ 'aliceMinVersion: {}\n'.format(str(click.style(module['aliceMinVersion']), fg='yellow'))
			+ 'pip requirements: {}\n'.format(click.style(', '.join(module['pipRequirements']), fg='yellow'))
			+ 'system requirements: {}\n\n'.format(click.style(', '.join(module['systemRequirements']), fg='yellow'))
			+ '+ Conditions:\n'
			+ '=============\n'
			+ 'lang: {}\n\n'.format(click.style(', '.join(module['conditions']['lang']), fg='yellow'))
		)

		urllib.request.urlretrieve(url, 'system/moduleInstallTickets/{}.install'.format(module_name))

	except Exception as e:
		click.secho('Failed to add the module', err=True, fg='red')


