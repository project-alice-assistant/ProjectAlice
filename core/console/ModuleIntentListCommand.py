from terminaltables import DoubleTable
import click

from core.snips.SamkillaManager import SamkillaManager
from config import settings

@click.command(name='module:intent:list')
@click.argument('module_name') # , help='Author\'s name'
@click.option('--intent', '-i', help='Show more data about specific intent')
@click.option('--full', '-f', is_flag=True, help='Display full description instead of truncated one')
def ModuleIntentListCommand(module_name: str, intent: str, full: bool):
	"""List intents and utterances for MODULE_NAME"""

	TABLE_DATA = [['Intents of module ' + module_name]]
	table_instance = DoubleTable(TABLE_DATA)
	click.secho('\n{}\n'.format(table_instance.table), fg='yellow')

	samkillaManager = SamkillaManager()
	_slotTypesModulesValues, _intentsModulesValues, _intentNameSkillMatching = samkillaManager.getDialogTemplatesMaps(
		runOnAssistantId=settings['supportedLanguages'][settings['activeLanguage']]['snipsProjectId'],
		languageFilter=settings['activeLanguage']
	)

	found = False
	if intent:
		TABLE_DATA = [['Utterances']]
		table_instance = DoubleTable(TABLE_DATA)

		for dtIntentName in _intentNameSkillMatching:
			if dtIntentName == intent:
				found = True

				for utterance in _intentsModulesValues[dtIntentName]['utterances']:
					if not full:
						utterance = (utterance[:100] + '..') if len(utterance) > 100 else utterance

					TABLE_DATA.append([ utterance or '-' ])
	else:
		TABLE_DATA = [['Intent', 'Description']]
		table_instance = DoubleTable(TABLE_DATA)

		for dtIntentName, dtModuleName in self._intentNameSkillMatching.items():
			if dtModuleName == module_name:
				found = True
				tDesc = self._intentsModulesValues[dtIntentName]['__otherattributes__']['description']

				if not full:
					tDesc = (tDesc[:100] + '..') if len(tDesc) > 100 else tDesc

				TABLE_DATA.append([ dtIntentName, tDesc or '-' ])

	if found:
		click.echo(table_instance.table)
	else:
		click.echo('\nNo intent found\n', err=True)