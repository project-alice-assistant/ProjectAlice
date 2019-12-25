from textwrap import dedent
import click
import urllib.request
import requests
from terminaltables import DoubleTable  # type: ignore
from core.base.SkillManager import SkillManager

@click.group()
def Add():
	"""Add new components to alice"""
	pass


@Add.command()
@click.argument('author_name')
@click.argument('skill_name')
def skill(author_name: str, skill_name: str):
	"""Add skill from dedicated repository to Alice"""

	TABLE_DATA = [['Skill Installer']]
	table_instance = DoubleTable(TABLE_DATA)
	click.secho(f'\n{table_instance.table}\n', fg='yellow')

	try:
		url = f'{SkillManager.GITHUB_BARE_BASE_URL}/{author_name}/{skill_name}/{skill_name}.install'
		req = requests.get(url)

		if req.status_code // 100 == 4:
			click.echo(dedent(f"""
				> Unknown {click.style(f'{author_name}/{skill_name}', fg='red')} pair
				- You can use {click.style('author list', fg='yellow')} to list all authors
				- You can use {click.style('skill list', fg='yellow')} to list all skills from an author
				"""),
				err=True
			)
			return

		theSkill = req.json()
		click.echo(dedent(f"""
			+ Informations:
			===============
			name: {click.style(str(theSkill['name']), fg='yellow')}
			version: {click.style(str(theSkill['version']), fg='yellow')}
			author: {click.style(theSkill['author'], fg='yellow')}
			maintainers: {click.style(', '.join(theSkill['maintainers']), fg='yellow')}
			description: {click.style(theSkill['desc'], fg='yellow')}
			aliceMinVersion: {click.style(str(theSkill['aliceMinVersion']), fg='yellow')}
			pip requirements: {click.style(', '.join(theSkill['pipRequirements']), fg='yellow')}
			system requirements: {click.style(', '.join(theSkill['systemRequirements']), fg='yellow')}

			+ Conditions:
			=============
			lang: {click.style(', '.join(theSkill['conditions']['lang']), fg='yellow')}
		"""))

		urllib.request.urlretrieve(url, f'system/skillInstallTickets/{skill_name}.install')

	except Exception as e:
		click.secho(f'Failed to add the skill: {e}', err=True, fg='red')


