# -*- coding: utf-8 -*-

import importlib
import os

from core.console.ConsoleApplication import ConsoleApplication
from core.base.ConfigManager import ConfigManager

#
# Application is the main entry point of a ConsoleApplication
#
class Application(ConsoleApplication):


	def __init__(self):
		self.commandsRegistered = False
		self.container = dict()
		super(Application, self).__init__('AliceConsole', 1)


	def run(self, input = None):
		self.container = dict()

		if not self.commandsRegistered:
			self.registerCommands()
			self.commandsRegistered = True

		for k,command in self.commands.items():
			command.setContainer(self.container)

		return super(Application, self).run(input)

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

		for moduleName, moduleData in modules.items():
			self.loadModuleCommands(moduleName)


	def loadModuleCommands(self, moduleName):
		commandsMountpoint = os.path.dirname(__file__) + '/../../modules/{}/console'.format(moduleName)

		if not os.path.isdir(commandsMountpoint): return

		for commandFile in os.listdir(commandsMountpoint):
			commandClassFile = commandFile.replace('.py', '')

			if commandClassFile.endswith("Command"):
				try:
					commandImport = importlib.import_module('modules.{}.console.{}'.format(moduleName, commandClassFile))
					klass = getattr(commandImport, commandClassFile)
					instance = klass()
					self.add(instance)
					return True
				except ImportError as e:
					continue
				except AttributeError as e:
					continue
				except Exception as e:
					continue

