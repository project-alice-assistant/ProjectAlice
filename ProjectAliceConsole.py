import click

from core.console.ModuleCommand import module
from core.console.AuthorCommand import author
from core.console.AssistantCommand import assistant
from core.console.IntentCommand import intent

@click.group(context_settings={'help_option_names':['--help', '-h']})
def cli():
    pass

cli.add_command(module)
cli.add_command(author)
cli.add_command(assistant)
cli.add_command(intent)

if __name__ == '__main__':
	cli()