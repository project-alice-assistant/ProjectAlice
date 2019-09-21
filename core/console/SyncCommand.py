import click
import logging.handlers
from core.base.SuperManager import SuperManager

@click.group()
def Sync():
	"""Sync components of alice"""
	pass

@Sync.command()
@click.option('--download', '-d', is_flag=True, help='Download the assistant after syncing')
def assistant(download: bool):
	"""Sync dialog templates for all modules"""

	_logger = logging.getLogger('ProjectAlice')
	_logger.setLevel(logging.INFO)
	_logger.addHandler(logging.StreamHandler())

	superManager = SuperManager(None)
	superManager.initManagers()

	samkillaManager = superManager.getManager('SamkillaManager')
	samkillaManager.onStart()

	try:
		samkillaManager.sync(download=download)
	except Exception as e:
		click.echo('Failed syncing with remote snips console {}'.format(e))
