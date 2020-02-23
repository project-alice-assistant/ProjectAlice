import click
import importlib.util
from pathlib import Path

from core.console.AddCommand import Add
from core.console.ListCommand import List
from core.console.SyncCommand import Sync
from core.console.UpdateCommand import Update

@click.group(context_settings={'help_option_names': ['--help', '-h']})
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

# import command namespaces from skills
for path in Path('skills').glob('*/console'):
	path = (path/path.parent.name).with_suffix('.py')
	if path.is_file():
		spec = importlib.util.spec_from_file_location(path.stem, path)
		skillCli = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(skillCli)
		if hasattr(skillCli, path.stem):
			cli.add_command(getattr(skillCli, path.stem))

if __name__ == '__main__':
	cli()

