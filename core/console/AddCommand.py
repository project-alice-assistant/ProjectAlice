from textwrap import dedent
import click
import urllib.request
import requests
from terminaltables import DoubleTable # type: ignore
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
	click.secho(f'\n{table_instance.table}\n', fg='yellow')

	try:
		url = f'{ModuleManager.GITHUB_BARE_BASE_URL}/{author_name}/{module_name}/{module_name}.install'
		req = requests.get(url)

		if req.status_code // 100 == 4:
			click.echo(dedent(f"""
				> Unknown {click.style(f'{author_name}/{module_name}', fg='red')} pair
				- You can use {click.style('author:list', fg='yellow')} to list all authors
				- You can use {click.style('module:list', fg='yellow')} to list all modules from an author
				"""),
				err=True
			)
			return

		module = req.json()
		click.echo(dedent(f"""
			+ Informations:
			===============
			name: {click.style(str(module['name']), fg='yellow')}
			version: {click.style(str(module['version']), fg='yellow')}
			author: {click.style(module['author'], fg='yellow')}
			maintainers: {click.style(', '.join(module['maintainers']), fg='yellow')}
			description: {click.style(module['desc'], fg='yellow')}
			aliceMinVersion: {click.style(str(module['aliceMinVersion']), fg='yellow')}
			pip requirements: {click.style(', '.join(module['pipRequirements']), fg='yellow')}
			system requirements: {click.style(', '.join(module['systemRequirements']), fg='yellow')}

			+ Conditions:
			=============
			lang: {click.style(', '.join(module['conditions']['lang']), fg='yellow')}
		"""))

		urllib.request.urlretrieve(url, f'system/moduleInstallTickets/{module_name}.install')

	except Exception as e:
		click.secho(f'Failed to add the module: {e}', err=True, fg='red')


