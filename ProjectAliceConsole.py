import click

from core.console.ModuleListCommand import ModuleListCommand
from core.console.ModuleIntentListCommand import ModuleIntentListCommand
from core.console.ModuleInstallCommand import ModuleInstallCommand
from core.console.AuthorListCommand import AuthorListCommand
from core.console.AssistantDownloadCommand import AssistantDownloadCommand
from core.console.AssistantSyncCommand import AssistantSyncCommand
from core.console.IntentListCommand import IntentListCommand

@click.group(context_settings={'help_option_names':['--help', '-h']})
def entry_point():
    pass

entry_point.add_command(ModuleListCommand)
entry_point.add_command(ModuleIntentListCommand)
entry_point.add_command(ModuleInstallCommand)
entry_point.add_command(AuthorListCommand)
entry_point.add_command(AssistantDownloadCommand)
entry_point.add_command(AssistantSyncCommand)
entry_point.add_command(IntentListCommand)

if __name__ == '__main__':
	entry_point()