import click

from core.console.AddCommand import Add
from core.console.ListCommand import List
from core.console.SyncCommand import Sync
from core.console.UpdateCommand import Update

@click.group(context_settings={'help_option_names':['--help', '-h']})
def cli():
	"""
	This is the Command Line Interface of Project Alice.
	Currently the following commands are supported.
	"""
	pass

cli.add_command(Add)
cli.add_command(List)
cli.add_command(Sync)
cli.add_command(Update)

if __name__ == '__main__':
	cli()