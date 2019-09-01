# -*- coding: utf-8 -*-

import importlib
from pathlib import Path

from core.commons import commons
from core.console.ConsoleApplication import ConsoleApplication
from core.base.ConfigManager import ConfigManager

#
# Application is the main entry point of a ConsoleApplication
#
class Application(ConsoleApplication):


	def __init__(self):
		self._commandsRegistered = False
		self._container = dict()
		super().__init__('AliceConsole', 1)


	def run(self, inputt: str = None):
		self._container = dict()

		if not self._commandsRegistered:
			self.registerCommands()
			self._commandsRegistered = True

		for command in self.commands.values():
			command.container(self._container)

		super().run(inputt)


	def registerCommands(self):
		from core.console.command.AssistantSyncCommand import AssistantSyncCommand
		self.add(AssistantSyncCommand())
		from core.console.command.AssistantDownloadCommand import AssistantDownloadCommand
		self.add(AssistantDownloadCommand())
		from core.console.command.AuthorListCommand import AuthorListCommand
		self.add(AuthorListCommand())
		from core.console.command.ModuleListCommand import ModuleListCommand
		self.add(ModuleListCommand())
		from core.console.command.ModuleInstallCommand import ModuleInstallCommand
		self.add(ModuleInstallCommand())
		from core.console.command.ModuleIntentListCommand import ModuleIntentListCommand
		self.add(ModuleIntentListCommand())
		from core.console.command.IntentListCommand import IntentListCommand
		self.add(IntentListCommand())

		configManager = ConfigManager(self)

		modules = configManager.getAliceConfigByName('modules')

		for moduleName in modules:
			self.loadModuleCommands(moduleName)


	def loadModuleCommands(self, moduleName: str) -> bool:
		commandsMountpoint = Path(commons.rootDir(), 'modules', moduleName, 'console')

		for commandFile in commandsMountpoint.glob('*Command.py'):
			commandClassFile = commandFile.with_suffix('').absolute().as_posix()

			try:
				commandImport = importlib.import_module('modules.{}.console.{}'.format(moduleName, commandClassFile))
				klass = getattr(commandImport, commandClassFile)
				instance = klass()
				self.add(instance)
				return True
			except Exception:
				pass

		return False
