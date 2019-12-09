import random
import click
import requests
from terminaltables import SingleTable # type: ignore
from core.base.ModuleManager import ModuleManager
from core.console.Helpers import OptionEatAll
from core.base.SuperManager import SuperManager

@click.group()
def List():
	"""List alice relevant data e.g. modules in the store"""
	pass


@List.command()
def authors():
	"""List module authors from the ProjectAliceModules repository"""

	tableData = [['Name']]
	tableInstance = SingleTable(tableData, click.style('Authors', fg='yellow'))

	try:
		req = requests.get(f'https://api.github.com/{ModuleManager.GITHUB_API_BASE_URL}')

		if req.status_code == 403:
			click.secho('Github API quota limitations reached\n', err=True, bg='red')
			return

		for author in req.json():
			tableData.append([
				author['name'],
			])

	except:
		click.secho('Error listing authors', err=True, fg='red')
	else:
		click.echo(tableInstance.table)

@List.command()
@click.option('--authors', '-a', 'authorsList', cls=OptionEatAll, help='specify authors to check')
@click.option('--full', '-f', is_flag=True, help='Display full description instead of truncated one')
def modules(authorsList: list, full: bool):
	"""List modules from the ProjectAliceModules repository"""

	if not authorsList:
		authorsList = list()
		req = requests.get(f'https://api.github.com/{ModuleManager.GITHUB_API_BASE_URL}')

		if req.status_code == 403:
			click.secho('Github API quota limitations reached\n', err=True, bg='red')
			return

		for author in req.json():
			authorsList.append(author['name'])

	maxDescriptionLength = 100

	for author in authorsList:

		tableData = [['Module Name', 'Version', 'Langs', 'Description']]
		tableInstance = SingleTable(tableData, click.style(author, fg='yellow'))

		try:
			req = requests.get(f'https://api.github.com/{ModuleManager.GITHUB_API_BASE_URL}/{author}')

			if req.status_code == 403:
				click.secho('Github API quota limitations reached\n', err=True, bg='red')
				return
			elif req.status_code // 100 == 4:
				click.echo(
					f"> Unknown author {click.style(author, fg='red')}\n"
					f"- You can use {click.style('author:list', fg='yellow')} to list all authors\n",
					err=True
				)
				return

			for module in req.json():
				moduleInstallFile = f"{ModuleManager.GITHUB_BARE_BASE_URL}/{author}/{module['name']}/{module['name']}.install"

				try:
					moduleDetails = requests.get(moduleInstallFile).json()
					tLangs = '|'.join(moduleDetails['conditions'].get('lang', ['-']))
					description = moduleDetails['desc']

					if not full:
						description = (description[:maxDescriptionLength] + '..') if len(description) > maxDescriptionLength else description

					tableData.append([
						moduleDetails['name'],
						moduleDetails['version'],
						tLangs,
						description
					])

				except:
					click.secho(f"Error get module {module['name']}", err=True, fg='red')
					raise

		except:
			click.secho('Error listing modules', err=True, fg='red')
		else:
			click.echo(tableInstance.table)

@List.command()
@click.option('--module', '-m', help='Show more data about specific module')
@click.option('--full', '-f', is_flag=True, help='Display full description instead of truncated one')
def intents(module: str, full: bool):
	"""List intents and utterances for a given module"""

	superManager = SuperManager(None)
	superManager.initManagers()

	samkillaManager = superManager.getManager('SamkillaManager')
	samkillaManager.onStart()
	languageManager = superManager.getManager('LanguageManager')
	languageManager.onStart()

	_slotTypesModulesValues, _intentsModulesValues, _intentNameSkillMatching = samkillaManager.getDialogTemplatesMaps(
		runOnAssistantId=languageManager.activeSnipsProjectId,
		languageFilter=languageManager.activeLanguage
	)

	maxDescriptionLength = 50
	found = False

	if module:
		tableData = [['Intent', 'Default', 'Description', 'Example']]
		tableInstance = SingleTable(tableData, click.style(module + ' intents', fg='yellow'))
		tableInstance.justify_columns[1] = 'center'

		for intentName, skillName in _intentNameSkillMatching.items():
			if skillName == module:
				found = True
				description = _intentsModulesValues[intentName]['__otherattributes__']['description']
				enabledByDefault = _intentsModulesValues[intentName]['__otherattributes__']['enabledByDefault']

				utterance = random.choice(list(_intentsModulesValues[intentName]['utterances']))

				if not full:
					description = (description[:maxDescriptionLength] + '..') if len(description) > maxDescriptionLength else description
					utterance = (utterance[:maxDescriptionLength] + '..') if len(utterance) > maxDescriptionLength else utterance

				tableData.append([
					intentName,
					'X' if enabledByDefault else '',
					description or '-',
					utterance or '-'
				])

	else:
		tableData = [['Intent', 'Default', 'Description', 'Example']]
		tableInstance = SingleTable(tableData, click.style('All intents', fg='yellow'))
		tableInstance.justify_columns[1] = 'center'
		found = True

		for intentName in _intentNameSkillMatching:
			description = _intentsModulesValues[intentName]['__otherattributes__']['description']
			enabledByDefault = _intentsModulesValues[intentName]['__otherattributes__']['enabledByDefault']

			utterance = random.choice(list(_intentsModulesValues[intentName]['utterances']))

			if not full:
				description = (description[:maxDescriptionLength] + '..') if len(description) > maxDescriptionLength else description
				utterance = (utterance[:maxDescriptionLength] + '..') if len(utterance) > maxDescriptionLength else utterance

			tableData.append([
				intentName,
				'X' if enabledByDefault else '',
				description or '-',
				utterance or '-'
			])

	if not found:
		click.echo('\nNo intent found\n', err=True)
	else:
		click.echo(tableInstance.table)
